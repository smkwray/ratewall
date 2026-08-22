"""Current benchmark and observed-overlay separation for RateWall."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from ratewall.databook.table_io import write_rows

DEFAULT_RUNTIME_TABLE_DIR = Path("outputs/tables")
DEFAULT_SOURCE_METHOD_DIR = Path("var/preliminary_scenario_results/source_method_matrix")
DEFAULT_HOLDER_TDC_BRIDGE_PATH = Path(
    "outputs/tables/ratewall_forecast_holder_tdc_consistency_bridge.csv"
)
DEFAULT_TDC_CHANNEL_PATH = Path("outputs/tables/ratewall_tdc_assumption_mode_channel.csv")

CURRENT_BENCHMARK_FIELDS = [
    "current_benchmark_row_id",
    "surface_id",
    "benchmark_id",
    "forecast_year",
    "reference_runtime_support_offset_row_id",
    "nominal_gdp_bil",
    "benchmark_numerator_bil",
    "benchmark_support_gdp_pct",
    "fixed_D_pp_gdp",
    "fixed_D_bil",
    "benchmark_ratewall_ratio",
    "ratio_recomputed_from_n_d",
    "exact_reproduction_of_runtime_ratio",
    "numerator_source_status",
    "denominator_source_status",
    "selected_current_row",
    "overlay_replacement_allowed",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

CURRENT_OVERLAY_MAP_FIELDS = [
    "current_overlay_map_row_id",
    "candidate_block_id",
    "source_method_block_id",
    "candidate_role",
    "surface_id",
    "source_object",
    "source_artifact_or_candidate",
    "local_source_status",
    "observed_value_available",
    "candidate_n_delta_bil",
    "candidate_d_bil",
    "candidate_ratewall_ratio",
    "replacement_gate_status",
    "benchmark_replacement_allowed",
    "central_current_value_changed",
    "overlap_guard_id",
    "required_next_model_step",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

CURRENT_OVERLAY_CANDIDATE_FIELDS = [
    "current_overlay_candidate_row_id",
    "candidate_id",
    "benchmark_row_id",
    "candidate_block_id",
    "forecast_year",
    "benchmark_numerator_bil",
    "benchmark_D_bil",
    "benchmark_ratewall_ratio",
    "candidate_n_delta_bil",
    "candidate_D_bil",
    "candidate_ratewall_ratio",
    "selected_current_row",
    "benchmark_replacement_allowed",
    "central_current_value_changed",
    "candidate_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

CURRENT_OVERLAY_ADMISSION_FIELDS = [
    "current_overlay_admission_row_id",
    "surface_id",
    "forecast_year",
    "benchmark_row_id",
    "source_bridge_row_handle",
    "tdc_channel_row_id",
    "public_interest_support_bil",
    "legacy_runtime_tdc_support_bil",
    "legacy_runtime_component_sum_bil",
    "benchmark_numerator_bil",
    "legacy_runtime_component_identity_error_bil",
    "tdc_full_bil",
    "direct_interest_overlap_cashflow_bil",
    "tdc_change_ex_overlap_bil",
    "beta",
    "chi",
    "beta_times_chi",
    "selected_beta_chi_tdc_support_bil",
    "selected_overlay_candidate_n_bil",
    "candidate_minus_benchmark_n_bil",
    "benchmark_D_bil",
    "selected_overlay_candidate_ratewall_ratio",
    "benchmark_ratewall_ratio",
    "public_interest_gate_status",
    "tdc_ex_overlap_gate_status",
    "denominator_gate_status",
    "overlap_gate_status",
    "replacement_gate_status",
    "selected_current_row",
    "benchmark_replacement_allowed",
    "central_current_value_changed",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

CURRENT_OBSERVED_OVERLAY_AUDIT_FIELDS = [
    "current_observed_overlay_audit_row_id",
    "check_id",
    "check_status",
    "row_count",
    "required_rule",
    "allowed_use",
    "blocked_use",
]


class CurrentObservedOverlayError(ValueError):
    """Raised when current-overlay inputs are inconsistent."""


def current_assumption_benchmark_rows(
    *,
    runtime_table_dir: str | Path = DEFAULT_RUNTIME_TABLE_DIR,
) -> list[dict[str, str]]:
    """Recast the existing current/static runtime result without changing it."""

    table_dir = Path(runtime_table_dir)
    overlay_rows = _read_required(
        table_dir / "ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv"
    )
    frontier_rows = _read_required(
        table_dir / "ratewall_runtime_annual_flow_support_offset_frontier_summary.csv"
    )
    scenario_rows = _read_required(
        table_dir / "ratewall_runtime_annual_flow_support_offset_scenarios.csv"
    )
    frontier_by_id = {row["frontier_row_id"]: row for row in frontier_rows}
    scenario_by_id = {row["runtime_support_offset_row_id"]: row for row in scenario_rows}
    out: list[dict[str, str]] = []
    for row in overlay_rows:
        source_row_id = row["default_runtime_frontier_row_id"]
        frontier = _required(frontier_by_id, source_row_id, "runtime frontier row")
        reference_row_id = frontier["reference_runtime_support_offset_row_id"]
        scenario = _required(
            scenario_by_id,
            reference_row_id,
            "reference runtime scenario row",
        )
        numerator = Decimal(scenario["numerator_total_bil"])
        nominal_gdp = Decimal(scenario["nominal_gdp_bil"])
        denominator_pp = Decimal(row["default_runtime_reference_denominator_center_pp_gdp"])
        denominator_bil = nominal_gdp * denominator_pp / Decimal("100")
        ratio = Decimal(row["default_runtime_reference_support_offset_100bp_year_equivalent"])
        recomputed = numerator / denominator_bil
        exact = recomputed == ratio
        if not exact:
            # The runtime table is rounded to 12 decimals. The benchmark row must still
            # disclose the exact recomputation rather than silently rewriting the source.
            exact = recomputed.quantize(Decimal("0.000000000001")) == ratio
        out.append(
            {
                "current_benchmark_row_id": (
                    f"current_assumption_benchmark::{row['forecast_year']}"
                ),
                "surface_id": "current_assumption_runtime",
                "benchmark_id": "current_assumption_benchmark",
                "forecast_year": row["forecast_year"],
                "reference_runtime_support_offset_row_id": reference_row_id,
                "nominal_gdp_bil": scenario["nominal_gdp_bil"],
                "benchmark_numerator_bil": scenario["numerator_total_bil"],
                "benchmark_support_gdp_pct": scenario["support_gdp_pct"],
                "fixed_D_pp_gdp": row[
                    "default_runtime_reference_denominator_center_pp_gdp"
                ],
                "fixed_D_bil": str(denominator_bil),
                "benchmark_ratewall_ratio": str(ratio),
                "ratio_recomputed_from_n_d": str(recomputed),
                "exact_reproduction_of_runtime_ratio": str(exact).lower(),
                "numerator_source_status": scenario["numerator_source_gate_status"],
                "denominator_source_status": row["overlay_status"],
                "selected_current_row": (
                    "true" if row["forecast_year"] == "2026" else "false"
                ),
                "overlay_replacement_allowed": "false",
                "allowed_use": "current_benchmark_snapshot_exact_runtime_recast",
                "blocked_use": (
                    "silent_observed_overlay_replacement;canonical_headline_promotion;"
                    "evidence_mode_claim;forecast_or_historical_selected_value"
                ),
                "claim_boundary": "current_benchmark_snapshot_no_model_value_change",
            }
        )
        if not source_row_id:
            raise CurrentObservedOverlayError("missing runtime frontier source id")
    return out


def current_observed_overlay_map_rows(
    *,
    source_method_dir: str | Path = DEFAULT_SOURCE_METHOD_DIR,
) -> list[dict[str, str]]:
    """Return source-led current overlay candidates without replacing the benchmark."""

    matrix = _read_required(Path(source_method_dir) / "ratewall_source_method_matrix.csv")
    by_block = {row["block_id"]: row for row in matrix}
    specs = [
        (
            "current_public_interest_observed_candidate",
            "current_public_interest_runtime",
            "benchmark_reference_not_replacement",
            "existing runtime row is the selected current benchmark; source-led split is not built here",
        ),
        (
            "current_tdc_ex_overlap_support_candidate",
            "current_tdc_decomposition",
            "candidate_overlay",
            "build exact ex-overlap TDC support gate before any current numerator use",
        ),
        (
            "current_fixed_D_observed_candidate",
            "current_denominator",
            "candidate_denominator_overlay",
            "build source-backed current denominator before replacing fixed current D",
        ),
        (
            "current_safe_yield_deposit_candidate",
            "realized_safe_yield_income",
            "candidate_residual_overlay",
            "build bank-first payer flow with bank_first_vs_recipient_flow_xor",
        ),
        (
            "current_zero_low_apr_credit_candidate",
            "zero_low_apr_credit",
            "candidate_minor_sensitivity_overlay",
            "build product stock and duration screen before any current sensitivity",
        ),
    ]
    out: list[dict[str, str]] = []
    for candidate_id, block_id, role, next_step in specs:
        source = _required(by_block, block_id, "source/method block")
        observed_available = (
            "true"
            if source["local_source_status"] == "present_local"
            and source["central_n_delta_bil_allowed"] == "true"
            and block_id == "current_public_interest_runtime"
            else "false"
        )
        out.append(
            {
                "current_overlay_map_row_id": f"current_overlay_map::{candidate_id}",
                "candidate_block_id": candidate_id,
                "source_method_block_id": block_id,
                "candidate_role": role,
                "surface_id": source["surface_id"],
                "source_object": source["source_object"],
                "source_artifact_or_candidate": source["source_artifact_or_candidate"],
                "local_source_status": source["local_source_status"],
                "observed_value_available": observed_available,
                "candidate_n_delta_bil": "",
                "candidate_d_bil": "",
                "candidate_ratewall_ratio": "",
                "replacement_gate_status": (
                    "benchmark_reference_selected"
                    if block_id == "current_public_interest_runtime"
                    else "blocked_requires_source_led_current_overlay_gate"
                ),
                "benchmark_replacement_allowed": "false",
                "central_current_value_changed": "false",
                "overlap_guard_id": source["overlap_guard_id"],
                "required_next_model_step": next_step,
                "allowed_use": "current_observed_overlay_planning_and_gate",
                "blocked_use": (
                    "silent_current_benchmark_replacement;canonical_headline_promotion;"
                    "evidence_mode_claim;central_current_N_or_D_change"
                ),
                "claim_boundary": "current_overlay_map_no_model_value_change",
            }
        )
    return out


def current_observed_overlay_candidate_rows(
    *,
    benchmark_rows: Sequence[Mapping[str, str]],
    overlay_rows: Sequence[Mapping[str, str]],
    admission_rows: Sequence[Mapping[str, str]] = (),
) -> list[dict[str, str]]:
    """Place overlay candidates beside the selected benchmark without selecting them."""

    benchmark = _single_selected_benchmark(benchmark_rows)
    admission_by_block = {
        "current_public_interest_runtime": (
            "public_interest_support_bil",
            "public_interest_gate_status",
        ),
        "current_tdc_decomposition": (
            "selected_beta_chi_tdc_support_bil",
            "tdc_ex_overlap_gate_status",
        ),
        "current_denominator": ("benchmark_D_bil", "denominator_gate_status"),
    }
    admission = admission_rows[0] if admission_rows else {}
    out: list[dict[str, str]] = []
    for row in overlay_rows:
        source_block_id = row["source_method_block_id"]
        candidate_n = row["candidate_n_delta_bil"]
        candidate_d = row["candidate_d_bil"]
        candidate_ratio = row["candidate_ratewall_ratio"]
        candidate_status = row["replacement_gate_status"]
        if admission and source_block_id in admission_by_block:
            value_field, status_field = admission_by_block[source_block_id]
            if source_block_id == "current_denominator":
                candidate_d = admission[value_field]
                candidate_ratio = benchmark["benchmark_ratewall_ratio"]
            else:
                candidate_n = admission[value_field]
                candidate_ratio = str(
                    _decimal(candidate_n) / _decimal(benchmark["fixed_D_bil"])
                )
            candidate_status = admission[status_field]
        out.append(
            {
                "current_overlay_candidate_row_id": (
                    f"current_overlay_candidate::{row['candidate_block_id']}"
                ),
                "candidate_id": row["candidate_block_id"],
                "benchmark_row_id": benchmark["current_benchmark_row_id"],
                "candidate_block_id": row["source_method_block_id"],
                "forecast_year": benchmark["forecast_year"],
                "benchmark_numerator_bil": benchmark["benchmark_numerator_bil"],
                "benchmark_D_bil": benchmark["fixed_D_bil"],
                "benchmark_ratewall_ratio": benchmark["benchmark_ratewall_ratio"],
                "candidate_n_delta_bil": candidate_n,
                "candidate_D_bil": candidate_d,
                "candidate_ratewall_ratio": candidate_ratio,
                "selected_current_row": "false",
                "benchmark_replacement_allowed": row["benchmark_replacement_allowed"],
                "central_current_value_changed": row["central_current_value_changed"],
                "candidate_status": candidate_status,
                "allowed_use": "current_overlay_candidate_review_only",
                "blocked_use": (
                    "selected_current_row;silent_current_benchmark_replacement;"
                    "canonical_headline_promotion;evidence_mode_claim"
                ),
                "claim_boundary": "current_overlay_candidate_no_model_value_change",
            }
        )
    return out


def current_observed_overlay_admission_rows(
    *,
    benchmark_rows: Sequence[Mapping[str, str]],
    holder_tdc_bridge_path: str | Path = DEFAULT_HOLDER_TDC_BRIDGE_PATH,
    tdc_channel_path: str | Path = DEFAULT_TDC_CHANNEL_PATH,
) -> list[dict[str, str]]:
    """Return R38 current-overlay decomposition and admission decision rows."""

    benchmark = _single_selected_benchmark(benchmark_rows)
    bridge = _current_bridge_row(Path(holder_tdc_bridge_path), benchmark["forecast_year"])
    tdc = _current_tdc_channel_row(Path(tdc_channel_path), benchmark["forecast_year"])
    public_interest = _decimal(bridge["interest_income_current_demand_support_bil"])
    legacy_tdc = _decimal(bridge["tdc_deposit_current_demand_support_bil"])
    legacy_sum = public_interest + legacy_tdc
    benchmark_n = _decimal(benchmark["benchmark_numerator_bil"])
    selected_tdc = _decimal(tdc["tdc_current_demand_support_bil"])
    candidate_n = public_interest + selected_tdc
    benchmark_d = _decimal(benchmark["fixed_D_bil"])
    beta = _decimal(tdc["tdc_materialization_beta"])
    chi = _decimal(tdc["deposit_current_demand_share"])
    beta_times_chi = beta * chi
    tdc_ex_overlap = _decimal(tdc["tdc_change_ex_overlap_bil"])
    formula_error = tdc_ex_overlap * beta_times_chi - selected_tdc
    replacement_gate = (
        "blocked_candidate_changes_current_N_requires_R40_current_object_decision"
        if candidate_n != benchmark_n
        else "blocked_no_named_replacement_surface"
    )
    return [
        {
            "current_overlay_admission_row_id": (
                f"current_overlay_admission::{benchmark['forecast_year']}::R38"
            ),
            "surface_id": "current_observed_overlay_candidate",
            "forecast_year": benchmark["forecast_year"],
            "benchmark_row_id": benchmark["current_benchmark_row_id"],
            "source_bridge_row_handle": (
                f"{bridge['forecast_year']}::{bridge['mpc_scenario']}::"
                f"{bridge['maturity_scenario']}::{bridge['holder_scenario']}"
            ),
            "tdc_channel_row_id": tdc["tdc_assumption_mode_channel_row_id"],
            "public_interest_support_bil": str(public_interest),
            "legacy_runtime_tdc_support_bil": str(legacy_tdc),
            "legacy_runtime_component_sum_bil": str(legacy_sum),
            "benchmark_numerator_bil": benchmark["benchmark_numerator_bil"],
            "legacy_runtime_component_identity_error_bil": str(legacy_sum - benchmark_n),
            "tdc_full_bil": tdc["tdc_change_bil"],
            "direct_interest_overlap_cashflow_bil": tdc[
                "direct_interest_overlap_cashflow_bil"
            ],
            "tdc_change_ex_overlap_bil": tdc["tdc_change_ex_overlap_bil"],
            "beta": tdc["tdc_materialization_beta"],
            "chi": tdc["deposit_current_demand_share"],
            "beta_times_chi": str(beta_times_chi),
            "selected_beta_chi_tdc_support_bil": str(selected_tdc),
            "selected_overlay_candidate_n_bil": str(candidate_n),
            "candidate_minus_benchmark_n_bil": str(candidate_n - benchmark_n),
            "benchmark_D_bil": benchmark["fixed_D_bil"],
            "selected_overlay_candidate_ratewall_ratio": str(candidate_n / benchmark_d),
            "benchmark_ratewall_ratio": benchmark["benchmark_ratewall_ratio"],
            "public_interest_gate_status": (
                "source_backed_runtime_public_interest_component_present"
            ),
            "tdc_ex_overlap_gate_status": (
                "pass_selected_beta_chi_ex_overlap_formula"
                if abs(formula_error) <= Decimal("1e-24")
                else "fail_selected_beta_chi_ex_overlap_formula"
            ),
            "denominator_gate_status": "current_fixed_D_comparison_only",
            "overlap_gate_status": (
                "pass_no_full_tdc_or_direct_interest_stacking;public_interest_plus_selected_tdc_is_candidate_only"
            ),
            "replacement_gate_status": replacement_gate,
            "selected_current_row": "false",
            "benchmark_replacement_allowed": "false",
            "central_current_value_changed": "false",
            "allowed_use": "R38_current_observed_overlay_admission_candidate",
            "blocked_use": (
                "selected_current_row;silent_current_benchmark_replacement;"
                "static_tdc_hook;canonical_headline_promotion;evidence_mode_claim"
            ),
            "claim_boundary": "current_overlay_admission_no_model_value_change",
        }
    ]


def current_observed_overlay_audit_rows(
    *,
    benchmark_rows: Sequence[Mapping[str, str]],
    overlay_rows: Sequence[Mapping[str, str]],
    candidate_rows: Sequence[Mapping[str, str]],
    admission_rows: Sequence[Mapping[str, str]] = (),
) -> list[dict[str, str]]:
    """Audit that R28 did not silently change the current estimate."""

    checks = [
        (
            "benchmark_runtime_ratio_reproduced",
            all(
                row["exact_reproduction_of_runtime_ratio"] == "true"
                for row in benchmark_rows
            ),
            len(benchmark_rows),
            "all benchmark rows reproduce the runtime ratio from N and D",
        ),
        (
            "single_selected_current_benchmark",
            sum(row["selected_current_row"] == "true" for row in benchmark_rows) == 1,
            len(benchmark_rows),
            "exactly one current benchmark row is selected",
        ),
        (
            "no_overlay_replacement",
            all(
                row["benchmark_replacement_allowed"] == "false"
                and row["central_current_value_changed"] == "false"
                for row in overlay_rows
            ),
            len(overlay_rows),
            "overlay rows cannot replace or change current central values",
        ),
        (
            "candidate_rows_not_selected",
            all(row["selected_current_row"] == "false" for row in candidate_rows),
            len(candidate_rows),
            "candidate rows stay review-only",
        ),
        (
            "R38_legacy_runtime_components_reproduce_benchmark",
            bool(admission_rows)
            and all(
                abs(_decimal(row["legacy_runtime_component_identity_error_bil"]))
                <= Decimal("1e-12")
                for row in admission_rows
            ),
            len(admission_rows),
            "legacy runtime public-interest plus legacy TDC components reproduce the benchmark N",
        ),
        (
            "R38_selected_tdc_uses_ex_overlap_beta_chi",
            bool(admission_rows)
            and all(
                row["tdc_ex_overlap_gate_status"]
                == "pass_selected_beta_chi_ex_overlap_formula"
                for row in admission_rows
            ),
            len(admission_rows),
            "selected current TDC candidate must use ex-overlap TDC times beta times chi",
        ),
        (
            "R38_no_current_benchmark_replacement",
            bool(admission_rows)
            and all(
                row["selected_current_row"] == "false"
                and row["benchmark_replacement_allowed"] == "false"
                and row["central_current_value_changed"] == "false"
                for row in admission_rows
            ),
            len(admission_rows),
            "R38 may expose current overlay candidates but cannot replace the benchmark",
        ),
    ]
    return [
        {
            "current_observed_overlay_audit_row_id": (
                f"current_observed_overlay_audit::{check_id}"
            ),
            "check_id": check_id,
            "check_status": "pass" if passed else "fail",
            "row_count": str(row_count),
            "required_rule": rule,
            "allowed_use": "current_overlay_gate_audit",
            "blocked_use": "silent_current_model_value_change",
        }
        for check_id, passed, row_count, rule in checks
    ]


def write_current_observed_overlay_outputs(
    output_dir: str | Path,
    *,
    benchmark_rows: list[dict[str, str]],
    overlay_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
    audit_rows: list[dict[str, str]],
    admission_rows: list[dict[str, str]] | None = None,
) -> dict[str, Path]:
    """Write R28 current benchmark and overlay outputs."""

    admission_rows = admission_rows or []
    out = Path(output_dir)
    outputs = {
        "benchmark_csv": out / "ratewall_current_assumption_benchmark.csv",
        "overlay_map_csv": out / "ratewall_current_observed_overlay_map.csv",
        "candidate_csv": out / "ratewall_current_observed_overlay_candidate.csv",
        "admission_csv": out / "ratewall_current_observed_overlay_admission.csv",
        "audit_csv": out / "ratewall_current_observed_overlay_audit.csv",
    }
    write_rows(outputs["benchmark_csv"], benchmark_rows, CURRENT_BENCHMARK_FIELDS)
    write_rows(outputs["overlay_map_csv"], overlay_rows, CURRENT_OVERLAY_MAP_FIELDS)
    write_rows(
        outputs["candidate_csv"], candidate_rows, CURRENT_OVERLAY_CANDIDATE_FIELDS
    )
    write_rows(
        outputs["admission_csv"],
        admission_rows,
        CURRENT_OVERLAY_ADMISSION_FIELDS,
    )
    write_rows(outputs["audit_csv"], audit_rows, CURRENT_OBSERVED_OVERLAY_AUDIT_FIELDS)
    return outputs


def _read_required(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise CurrentObservedOverlayError(f"missing required input: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _required(
    mapping: Mapping[str, Mapping[str, str]], key: str, label: str
) -> Mapping[str, str]:
    try:
        return mapping[key]
    except KeyError as exc:
        raise CurrentObservedOverlayError(f"missing {label}: {key}") from exc


def _single_selected_benchmark(
    rows: Sequence[Mapping[str, str]],
) -> Mapping[str, str]:
    selected = [row for row in rows if row["selected_current_row"] == "true"]
    if len(selected) != 1:
        raise CurrentObservedOverlayError(
            f"expected exactly one selected benchmark row, found {len(selected)}"
        )
    return selected[0]


def _current_bridge_row(path: Path, forecast_year: str) -> Mapping[str, str]:
    rows = [
        row
        for row in _read_required(path)
        if row["forecast_year"] == forecast_year
        and row["mpc_scenario"] == "base_mpc_10pct"
        and row["maturity_scenario"] == "current_wam_cbo_rate_path"
        and row["holder_scenario"] == "current_holder_distribution"
    ]
    if len(rows) != 1:
        raise CurrentObservedOverlayError(
            f"expected one current bridge row for {forecast_year}, found {len(rows)}"
        )
    return rows[0]


def _current_tdc_channel_row(path: Path, forecast_year: str) -> Mapping[str, str]:
    rows = [
        row
        for row in _read_required(path)
        if row["forecast_year"] == forecast_year
        and row["channel_conversion_profile_id"] == "base"
        and row["maturity_scenario"] == "current_wam_cbo_rate_path"
        and row["holder_scenario"] == "current_holder_distribution"
    ]
    if len(rows) != 1:
        raise CurrentObservedOverlayError(
            f"expected one current TDC channel row for {forecast_year}, found {len(rows)}"
        )
    return rows[0]


def _decimal(value: str) -> Decimal:
    return Decimal(value or "0")
