"""Preliminary Assumption Mode scenario-result surface and simple visuals."""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ratewall.databook.tdcsim_cbo_contracts import (
    TDCSIM_CBO_SCENARIO_RUNS_DIR,
    tdcsim_cbo_model_scenario_interpretation_synthesis_rows_from_directory,
    tdcsim_cbo_model_scenario_materiality_classification_rows_from_directory,
    tdcsim_cbo_model_scenario_summary_rows_from_directory,
)


FRBUS_STRUCTURAL_TERM_PREMIUM_BENCHMARK_LABEL = (
    "FRB/US structural Assumption Mode denominator route"
)
FRBUS_STRUCTURAL_CLAIM_BOUNDARY = (
    "final Assumption Mode structural denominator route; not empirical same-axis "
    "Treasury evidence; not local econometric evidence; not Evidence Mode; not "
    "denominator-prior update; not runtime denominator recalibration; not "
    "headline/path-ratio replacement"
)

PRELIMINARY_SCENARIO_RESULT_FIELDS = [
    "preliminary_scenario_result_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_label",
    "summary_role",
    "comparison_group",
    "scenario_family",
    "baseline_scenario_id",
    "term_premium_tier",
    "total_current_demand_support_bil",
    "delta_total_current_demand_support_bil",
    "delta_tdc_current_demand_support_bil",
    "delta_direct_treasury_current_demand_support_bil",
    "delta_bank_treasury_current_demand_support_bil",
    "support_mechanism_profile",
    "dominant_delta_support_component",
    "dominant_delta_support_component_bil",
    "path_bps_year",
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
    "beta_chi_min_delta_ratewall_ratio",
    "beta_chi_max_delta_ratewall_ratio",
    "denominator_bound_theta_values",
    "denominator_bound_min_moving_delta_ratewall_ratio_vs_baseline",
    "denominator_bound_max_moving_delta_ratewall_ratio_vs_baseline",
    "denominator_bound_sign_stability_status",
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


class PreliminaryScenarioResultError(ValueError):
    """Raised when preliminary scenario rows cannot be assembled consistently."""


def preliminary_scenario_result_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
) -> list[dict[str, str]]:
    """Load the current TDCSim/CBO suite and build preliminary result rows."""

    return preliminary_scenario_result_rows(
        summary_rows=tdcsim_cbo_model_scenario_summary_rows_from_directory(
            suite_dir
        ),
        synthesis_rows=(
            tdcsim_cbo_model_scenario_interpretation_synthesis_rows_from_directory(
                suite_dir
            )
        ),
        materiality_rows=(
            tdcsim_cbo_model_scenario_materiality_classification_rows_from_directory(
                suite_dir
            )
        ),
    )


def preliminary_scenario_result_rows(
    *,
    summary_rows: Iterable[Mapping[str, str]],
    synthesis_rows: Iterable[Mapping[str, str]],
    materiality_rows: Iterable[Mapping[str, str]] = (),
) -> list[dict[str, str]]:
    """Combine existing model surfaces into a reader-facing preliminary table."""

    summaries = _by_key(summary_rows, "summary")
    synthesis = _by_key(synthesis_rows, "synthesis")
    materiality = _by_key(materiality_rows, "materiality", require_unique=False)
    out: list[dict[str, str]] = []
    for key, summary in summaries.items():
        if key not in synthesis:
            raise PreliminaryScenarioResultError(
                f"missing synthesis row for {key[0]}::{key[1]}"
            )
        syn = synthesis[key]
        mat = materiality.get(key, {})
        moving_ratio = _decimal(syn["selected_moving_ratewall_ratio"])
        frozen_ratio = _decimal(summary["level_ratewall_ratio"])
        moving_denominator = _decimal(syn["selected_moving_denominator_bil"])
        out.append(
            {
                "preliminary_scenario_result_row_id": (
                    "preliminary_scenario_result::"
                    f"{summary['fiscal_year']}::{summary['scenario_id']}"
                ),
                "fiscal_year": summary["fiscal_year"],
                "scenario_id": summary["scenario_id"],
                "scenario_label": summary["model_interpretation"],
                "summary_role": summary["summary_role"],
                "comparison_group": summary["comparison_group"],
                "scenario_family": mat.get("scenario_family", ""),
                "baseline_scenario_id": summary["baseline_scenario_id"],
                "term_premium_tier": summary["term_premium_tier"],
                "total_current_demand_support_bil": _fmt(
                    moving_ratio * moving_denominator
                ),
                "delta_total_current_demand_support_bil": summary[
                    "delta_total_current_demand_support_bil"
                ],
                "delta_tdc_current_demand_support_bil": summary[
                    "delta_tdc_current_demand_support_bil"
                ],
                "delta_direct_treasury_current_demand_support_bil": summary[
                    "delta_direct_treasury_current_demand_support_bil"
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
                "path_bps_year": syn["curve_effective_overlay_bp"],
                "selected_denominator_response_profile_id": syn[
                    "selected_denominator_response_profile_id"
                ],
                "selected_denominator_response_label": (
                    FRBUS_STRUCTURAL_TERM_PREMIUM_BENCHMARK_LABEL
                ),
                "selected_denominator_response_coefficient": syn[
                    "selected_denominator_response_coefficient"
                ],
                "selected_denominator_response_coefficient_unit": syn[
                    "selected_denominator_response_coefficient_unit"
                ],
                "selected_denominator_response_status": syn[
                    "selected_denominator_response_status"
                ],
                "frozen_denominator_bil": _selected_frozen_denominator(summary, syn),
                "selected_delta_denominator_bil": syn[
                    "selected_delta_denominator_bil"
                ],
                "selected_moving_denominator_bil": syn[
                    "selected_moving_denominator_bil"
                ],
                "frozen_ratewall_ratio": summary["level_ratewall_ratio"],
                "frozen_delta_ratewall_ratio_vs_baseline": summary[
                    "delta_ratewall_ratio_vs_baseline"
                ],
                "selected_moving_ratewall_ratio": syn[
                    "selected_moving_ratewall_ratio"
                ],
                "selected_moving_delta_ratewall_ratio_vs_baseline": syn[
                    "selected_moving_delta_ratewall_ratio_vs_baseline"
                ],
                "moving_minus_frozen_ratewall_ratio": _fmt(
                    moving_ratio - frozen_ratio
                ),
                "selected_wall_hit_status": (
                    "wall_hit" if moving_ratio >= Decimal("1") else "no_hit"
                ),
                "beta_chi_sign_stability_status": syn[
                    "beta_chi_sign_stability_status"
                ],
                "beta_chi_min_delta_ratewall_ratio": syn[
                    "beta_chi_min_delta_ratewall_ratio"
                ],
                "beta_chi_max_delta_ratewall_ratio": syn[
                    "beta_chi_max_delta_ratewall_ratio"
                ],
                "denominator_bound_theta_values": syn[
                    "denominator_bound_theta_values"
                ],
                "denominator_bound_min_moving_delta_ratewall_ratio_vs_baseline": (
                    syn[
                        "denominator_bound_min_moving_delta_ratewall_ratio_vs_baseline"
                    ]
                ),
                "denominator_bound_max_moving_delta_ratewall_ratio_vs_baseline": (
                    syn[
                        "denominator_bound_max_moving_delta_ratewall_ratio_vs_baseline"
                    ]
                ),
                "denominator_bound_sign_stability_status": syn[
                    "denominator_bound_sign_stability_status"
                ],
                "model_relevance_class": mat.get("model_relevance_class", ""),
                "recommended_use": mat.get(
                    "recommended_use",
                    "preliminary_assumption_mode_interpretation_only",
                ),
                "allowed_use": "preliminary_assumption_mode_scenario_readout",
                "blocked_use": (
                    "canonical_headline_promotion;denominator_recalibration;"
                    "default_runtime_anchor;evidence_mode_claim;"
                    "causal_market_yield_estimate;denominator_prior_update;"
                    "path_ratio_denominator_replacement;release_headline_claim;"
                    "local_econometric_denominator_claim"
                ),
                "claim_boundary": FRBUS_STRUCTURAL_CLAIM_BOUNDARY,
                "canonical_ratio_entry": "false",
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "denominator_prior_update_allowed": "false",
            }
        )
    return sorted(out, key=lambda row: (int(row["fiscal_year"]), row["scenario_id"]))


def write_preliminary_scenario_outputs(
    output_dir: str | Path,
    *,
    rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    """Write CSV, SVG diagnostics, and a short economist-facing readout."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "csv": out / "ratewall_preliminary_scenario_results.csv",
        "ranking_svg": out / "scenario_selected_moving_delta_rw.svg",
        "bridge_svg": out / "rate_changing_frozen_vs_moving_rw.svg",
        "scatter_svg": out / "curve_path_to_delta_d.svg",
        "components_svg": out / "central_rate_scenario_components.svg",
        "readout_md": out / "economist_readout.md",
    }
    _write_csv(paths["csv"], rows)
    paths["ranking_svg"].write_text(
        selected_delta_ratewall_svg(rows),
        encoding="utf-8",
    )
    paths["bridge_svg"].write_text(
        frozen_vs_moving_ratewall_svg(rows),
        encoding="utf-8",
    )
    paths["scatter_svg"].write_text(path_to_delta_d_svg(rows), encoding="utf-8")
    paths["components_svg"].write_text(
        central_rate_components_svg(rows),
        encoding="utf-8",
    )
    paths["readout_md"].write_text(
        economist_readout_markdown(rows),
        encoding="utf-8",
    )
    return paths


def selected_delta_ratewall_svg(rows: Sequence[Mapping[str, str]]) -> str:
    """Return a simple horizontal bar chart of selected moving delta RW."""

    ranked = sorted(
        rows,
        key=lambda row: abs(
            _decimal(row["selected_moving_delta_ratewall_ratio_vs_baseline"])
        ),
        reverse=True,
    )
    return _bar_svg(
        ranked,
        value_field="selected_moving_delta_ratewall_ratio_vs_baseline",
        title="Selected FRB/US moving-D delta RateWall vs baseline",
        width=980,
    )


def frozen_vs_moving_ratewall_svg(rows: Sequence[Mapping[str, str]]) -> str:
    """Return a grouped bar chart for frozen and selected moving RW."""

    rate_rows = [row for row in rows if _decimal(row["path_bps_year"]) != 0]
    rate_rows = sorted(rate_rows, key=lambda row: row["scenario_id"])
    width = 980
    row_h = 52
    height = 80 + row_h * max(1, len(rate_rows))
    max_value = max(
        [
            *(_decimal(row["frozen_ratewall_ratio"]) for row in rate_rows),
            *(_decimal(row["selected_moving_ratewall_ratio"]) for row in rate_rows),
            Decimal("0.01"),
        ]
    )
    scale = Decimal(str(width - 420)) / max_value
    parts = [_svg_header(width, height), _svg_text(20, 28, "Frozen vs selected moving RateWall for rate-changing scenarios", 16)]
    y = 60
    for row in rate_rows:
        label = _short_label(row)
        frozen = _decimal(row["frozen_ratewall_ratio"])
        moving = _decimal(row["selected_moving_ratewall_ratio"])
        parts.append(_svg_text(20, y + 15, label, 11))
        parts.append(_rect(330, y, frozen * scale, 14, "#9ca3af"))
        parts.append(_rect(330, y + 18, moving * scale, 14, "#2563eb"))
        parts.append(_svg_text(340 + int(max(frozen, moving) * scale), y + 14, f"frozen {frozen:.4f} / moving {moving:.4f}", 10))
        y += row_h
    parts.append(_svg_text(330, height - 18, "gray=frozen D, blue=selected FRB/US moving D", 11))
    parts.append("</svg>")
    return "\n".join(parts)


def path_to_delta_d_svg(rows: Sequence[Mapping[str, str]]) -> str:
    """Return a scatter diagnostic of curve path vs selected delta D."""

    width = 760
    height = 440
    plot_x = 80
    plot_y = 50
    plot_w = 600
    plot_h = 300
    points = [row for row in rows if _decimal(row["path_bps_year"]) != 0]
    max_x = max([abs(_decimal(row["path_bps_year"])) for row in points] + [Decimal("1")])
    max_y = max(
        [abs(_decimal(row["selected_delta_denominator_bil"])) for row in points]
        + [Decimal("1")]
    )
    parts = [_svg_header(width, height), _svg_text(20, 28, "Curve path to selected delta D", 16)]
    parts.append(_line(plot_x, plot_y + plot_h / 2, plot_x + plot_w, plot_y + plot_h / 2, "#d1d5db"))
    parts.append(_line(plot_x + plot_w / 2, plot_y, plot_x + plot_w / 2, plot_y + plot_h, "#d1d5db"))
    for row in points:
        x = plot_x + plot_w / 2 + float(_decimal(row["path_bps_year"]) / max_x) * plot_w / 2
        y = plot_y + plot_h / 2 - float(_decimal(row["selected_delta_denominator_bil"]) / max_y) * plot_h / 2
        color = "#dc2626" if _decimal(row["path_bps_year"]) > 0 else "#16a34a"
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{color}" />')
        parts.append(_svg_text(x + 8, y + 4, _short_label(row), 10))
    parts.append(_svg_text(plot_x, height - 38, "x = path_bps_year; y = selected_delta_denominator_bil", 11))
    parts.append(_svg_text(plot_x, height - 20, "Positive rate path increases D; negative rate path decreases D.", 11))
    parts.append("</svg>")
    return "\n".join(parts)


def central_rate_components_svg(rows: Sequence[Mapping[str, str]]) -> str:
    """Return a compact component chart for central shorter/longer rate rows."""

    target_ids = {
        "tdcsim_issuance_empirical_shorter_termprem_down_central_v1",
        "tdcsim_issuance_empirical_longer_termprem_up_central_v1",
    }
    selected = [row for row in rows if row["scenario_id"] in target_ids]
    fields = [
        ("delta_tdc_current_demand_support_bil", "TDC", "#2563eb"),
        ("delta_direct_treasury_current_demand_support_bil", "Direct", "#7c3aed"),
        ("delta_bank_treasury_current_demand_support_bil", "Bank", "#0891b2"),
        ("selected_delta_denominator_bil", "D move", "#ea580c"),
    ]
    max_abs = max(
        [abs(_decimal(row[field])) for row in selected for field, _, _ in fields]
        + [Decimal("1")]
    )
    width = 980
    height = 110 + 56 * max(1, len(selected) * len(fields))
    scale = Decimal("240") / max_abs
    zero_x = 430
    parts = [_svg_header(width, height), _svg_text(20, 28, "Central rate scenario components, billions", 16)]
    y = 60
    for row in sorted(selected, key=lambda item: item["scenario_id"]):
        parts.append(_svg_text(20, y + 12, _short_label(row), 11))
        for field, label, color in fields:
            value = _decimal(row[field])
            x = zero_x if value >= 0 else zero_x + int(value * scale)
            parts.append(_svg_text(275, y + 12, label, 10))
            parts.append(_rect(x, y, abs(value * scale), 14, color))
            parts.append(_svg_text(zero_x + int(value * scale) + 8, y + 12, f"{value:.2f}", 10))
            y += 22
        y += 12
    parts.append(_line(zero_x, 50, zero_x, height - 35, "#111827"))
    parts.append(_svg_text(20, height - 18, "D move is denominator movement, not numerator support.", 11))
    parts.append("</svg>")
    return "\n".join(parts)


def economist_readout_markdown(rows: Sequence[Mapping[str, str]]) -> str:
    """Return a concise preliminary economist-facing readout."""

    baseline = _baseline(rows)
    largest = sorted(
        [row for row in rows if row["scenario_id"] != baseline["scenario_id"]],
        key=lambda row: abs(
            _decimal(row["selected_moving_delta_ratewall_ratio_vs_baseline"])
        ),
        reverse=True,
    )[:5]
    lines = [
        "# RateWall Preliminary Scenario Readout",
        "",
        "RateWall is `RW = N / D`. `N` is current-demand support; `D` is the conventional-demand shortfall. The wall is hit when `RW >= 1`.",
        "",
        "## Core Assumptions",
        "",
        "- Scenario numerator rows come from verified TDCSim/CBO accounting channels.",
        "- TDC support follows `N_TDC = delta_TDC_ex_overlap * beta * chi`.",
        "- Rate-changing scenarios move `D` using the selected FRB/US structural Assumption Mode denominator route.",
        f"- Selected coefficient: `c_D={baseline['selected_denominator_response_coefficient']}`.",
        "- Unit: `fraction_of_frozen_denominator_per_100bp_year`.",
        f"- Claim boundary: {FRBUS_STRUCTURAL_CLAIM_BOUNDARY}.",
        "- Legacy `c_D=0.125` is a sensitivity comparison, not the selected route and not a confidence interval.",
        "",
        "## Baseline",
        "",
        f"- Baseline scenario: `{baseline['scenario_id']}`.",
        f"- Frozen RW: `{baseline['frozen_ratewall_ratio']}`.",
        f"- Selected moving-D RW: `{baseline['selected_moving_ratewall_ratio']}`.",
        f"- Wall status: `{baseline['selected_wall_hit_status']}`.",
        "",
        "## Largest Preliminary Scenario Movements",
        "",
    ]
    for row in largest:
        lines.append(
            "- "
            f"`{row['scenario_id']}`: selected moving delta RW "
            f"`{row['selected_moving_delta_ratewall_ratio_vs_baseline']}`, "
            f"path `{row['path_bps_year']}` bp-year, "
            f"delta D `{row['selected_delta_denominator_bil']}` bn, "
            f"recommended use `{row['recommended_use']}`."
        )
    lines.extend(
        [
            "",
            "## Interpretation Rule",
            "",
            "For non-rate scenarios, `D` should remain unchanged. For rate-changing scenarios, compare frozen RW and selected moving-D RW side by side. A rate-down path reduces `D` and can raise RW even if numerator support is unchanged; a rate-up path raises `D` and can lower RW.",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_csv(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PRELIMINARY_SCENARIO_RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _bar_svg(
    rows: Sequence[Mapping[str, str]],
    *,
    value_field: str,
    title: str,
    width: int,
) -> str:
    row_h = 34
    height = 72 + row_h * max(1, len(rows))
    max_abs = max([abs(_decimal(row[value_field])) for row in rows] + [Decimal("0.01")])
    zero_x = 450
    scale = Decimal(str((width - zero_x - 80) / 1)) / max_abs
    parts = [_svg_header(width, height), _svg_text(20, 28, title, 16)]
    parts.append(_line(zero_x, 48, zero_x, height - 26, "#111827"))
    y = 56
    for row in rows:
        value = _decimal(row[value_field])
        x = zero_x if value >= 0 else zero_x + int(value * scale)
        color = "#2563eb" if value >= 0 else "#dc2626"
        parts.append(_svg_text(20, y + 12, _short_label(row), 10))
        parts.append(_rect(x, y, abs(value * scale), 16, color))
        parts.append(_svg_text(zero_x + int(value * scale) + 8, y + 12, f"{value:.4f}", 10))
        y += row_h
    parts.append("</svg>")
    return "\n".join(parts)


def _by_key(
    rows: Iterable[Mapping[str, str]],
    label: str,
    *,
    require_unique: bool = True,
) -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["scenario_id"], row["fiscal_year"])
        if require_unique and key in out:
            raise PreliminaryScenarioResultError(f"duplicate {label} row for {key}")
        out[key] = dict(row)
    return out


def _selected_frozen_denominator(
    summary: Mapping[str, str],
    synthesis: Mapping[str, str],
) -> str:
    moving = _decimal(synthesis["selected_moving_denominator_bil"])
    delta = _decimal(synthesis["selected_delta_denominator_bil"])
    if synthesis["selected_delta_denominator_bil"]:
        return _fmt(moving - delta)
    return summary.get("frozen_denominator_bil", "")


def _baseline(rows: Sequence[Mapping[str, str]]) -> Mapping[str, str]:
    for row in rows:
        if row["scenario_id"] == row["baseline_scenario_id"]:
            return row
    raise PreliminaryScenarioResultError("missing baseline row")


def _short_label(row: Mapping[str, str]) -> str:
    label = row.get("scenario_label") or row["scenario_id"]
    label = label.replace("tdcsim_", "").replace("_v1", "")
    return label[:58]


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise PreliminaryScenarioResultError(f"invalid decimal value: {value}") from exc


def _fmt(value: Decimal) -> str:
    if value == value.to_integral():
        return str(value.quantize(Decimal("1")))
    return format(value.normalize(), "f")


def _svg_header(width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" fill="white"/>'
    )


def _svg_text(x: float, y: float, text: str, size: int) -> str:
    escaped = (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial, sans-serif" '
        f'font-size="{size}" fill="#111827">{escaped}</text>'
    )


def _rect(
    x: float | Decimal,
    y: float | Decimal,
    width: float | Decimal,
    height: int,
    fill: str,
) -> str:
    return (
        f'<rect x="{float(x):.1f}" y="{float(y):.1f}" '
        f'width="{float(width):.1f}" height="{height}" fill="{fill}" />'
    )


def _line(x1: float, y1: float, x2: float, y2: float, stroke: str) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="1" />'
    )
