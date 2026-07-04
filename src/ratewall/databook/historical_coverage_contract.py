"""Historical coverage and extension contract for RateWall T3."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from ratewall.databook.historical_tdc_source_registry import (
    DEFAULT_HISTORICAL_PROVISIONAL_DIR,
    historical_tdc_source_registry_rows,
    validate_historical_tdc_source_registry,
)
from ratewall.databook.table_io import write_rows

DEFAULT_OUTPUT_DIR = Path("var/preliminary_scenario_results/historical_coverage_contract")

HISTORICAL_COVERAGE_CONTRACT_FIELDS = [
    "historical_coverage_contract_row_id",
    "route_id",
    "coverage_window_start",
    "coverage_window_end",
    "route_role",
    "tdc_panel_coverage_start",
    "tdc_panel_coverage_end",
    "tdc_selected_column_nonnull_start",
    "tdc_selected_column_nonnull_end",
    "tdc_source_basis_chosen",
    "beta_window_start",
    "beta_window_end",
    "beta_selector_status",
    "selected_historical_n_includes_tdc",
    "tdc_centrality",
    "rate_or_scenario_attribution_status",
    "demand_translation_status",
    "selection_gate_status",
    "classifier_allowed",
    "historical_n_formula",
    "historical_n_additive_terms",
    "nonadditive_decomposition_terms",
    "same_quarter_numerator_coverage_status",
    "same_quarter_denominator_coverage_status",
    "final_classifier_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

HISTORICAL_EXTENSION_FEASIBILITY_FIELDS = [
    "historical_extension_feasibility_row_id",
    "route_id",
    "target_window_start",
    "target_window_end",
    "feasibility_status",
    "fail_closed_label",
    "required_next_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

HISTORICAL_NUMERATOR_PANEL_FIELDS = [
    "historical_numerator_panel_row_id",
    "period",
    "assumption_case",
    "tdc_ex_overlap_support_bil",
    "public_interest_net_block_partial_bil",
    "direct_treasury_interest_decomposition_bil",
    "historical_n_context_bil",
    "historical_n_formula",
    "selected_historical_n_includes_tdc",
    "classifier_allowed",
    "source_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

HISTORICAL_TDC_MECHANISM_PANEL_FIELDS = [
    "historical_tdc_mechanism_panel_row_id",
    "period",
    "assumption_case",
    "tdc_ex_overlap_support_bil",
    "public_interest_net_block_partial_bil",
    "tdc_source_basis_chosen",
    "beta_policy",
    "chi_policy",
    "tdc_centrality",
    "selected_historical_n_includes_tdc",
    "classifier_allowed",
    "post_2025q4_tdc_source_update_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


class HistoricalCoverageContractError(ValueError):
    """Raised when historical coverage contract rows violate T3."""


def historical_coverage_contract_rows(
    *,
    source_registry_rows: Sequence[Mapping[str, str]] | None = None,
    historical_provisional_dir: str | Path = DEFAULT_HISTORICAL_PROVISIONAL_DIR,
) -> list[dict[str, str]]:
    """Return route-level historical coverage contract rows."""

    registry = (
        list(source_registry_rows)
        if source_registry_rows is not None
        else historical_tdc_source_registry_rows()
    )
    validate_historical_tdc_source_registry(registry)
    numerator_bounds, denominator_bounds = _implemented_bounds(historical_provisional_dir)
    rows = []
    for route in registry:
        is_implemented = route["route_id"] == "implemented_short_panel"
        rows.append(
            {
                "historical_coverage_contract_row_id": (
                    f"historical_coverage_contract::{route['route_id']}"
                ),
                "route_id": route["route_id"],
                "coverage_window_start": route["expected_window_start"],
                "coverage_window_end": route["expected_window_end"],
                "route_role": route["route_role"],
                "tdc_panel_coverage_start": route[
                    "downstream_selected_column_nonnull_start"
                ],
                "tdc_panel_coverage_end": route[
                    "downstream_selected_column_nonnull_end"
                ],
                "tdc_selected_column_nonnull_start": route[
                    "upstream_selected_column_nonnull_start"
                ],
                "tdc_selected_column_nonnull_end": route[
                    "upstream_selected_column_nonnull_end"
                ],
                "tdc_source_basis_chosen": route["tdc_source_basis_chosen"],
                "beta_window_start": "normal_forward_assumption_constant",
                "beta_window_end": "normal_forward_assumption_constant",
                "beta_selector_status": (
                    "normal_forward_constant_beta_context_only_not_runtime_selector"
                ),
                "selected_historical_n_includes_tdc": "false",
                "tdc_centrality": "diagnostic_context",
                "rate_or_scenario_attribution_status": (
                    "historical_context_not_rate_scenario_selected"
                ),
                "demand_translation_status": "context_translation_not_selected_n",
                "selection_gate_status": "blocked_historical_nonclassifier_policy",
                "classifier_allowed": "false",
                "historical_n_formula": (
                    "tdc_ex_overlap_support_bil + public_interest_net_block_partial_bil"
                ),
                "historical_n_additive_terms": (
                    "tdc_ex_overlap_support_bil;public_interest_net_block_partial_bil"
                ),
                "nonadditive_decomposition_terms": (
                    "direct_treasury_interest_bil_inside_public_interest_context"
                ),
                "same_quarter_numerator_coverage_status": (
                    f"implemented_numerator_panel::{numerator_bounds[0]}::{numerator_bounds[1]}"
                    if is_implemented
                    else route["selected_column_coverage_status"]
                ),
                "same_quarter_denominator_coverage_status": (
                    f"implemented_denominator_panel::{denominator_bounds[0]}::{denominator_bounds[1]}"
                    if is_implemented
                    else "same_quarter_denominator_required_before_rw"
                ),
                "final_classifier_status": "closed_nonclassifier",
                "allowed_use": "historical_coverage_and_extension_contract",
                "blocked_use": "final_historical_classifier;selected_historical_n",
                "claim_boundary": "historical_contract_context_not_classifier",
            }
        )
    validate_historical_coverage_contract(rows)
    return rows


def historical_extension_feasibility_rows(
    *,
    coverage_rows: Sequence[Mapping[str, str]],
    source_registry_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Return fail-closed feasibility rows for historical extension routes."""

    validate_historical_coverage_contract(coverage_rows)
    validate_historical_tdc_source_registry(source_registry_rows)
    source_by_route = {row["route_id"]: row for row in source_registry_rows}
    rows = []
    for row in coverage_rows:
        source = source_by_route[row["route_id"]]
        passed = source["route_status"].startswith("pass") or row[
            "route_id"
        ] == "implemented_short_panel"
        rows.append(
            {
                "historical_extension_feasibility_row_id": (
                    f"historical_extension_feasibility::{row['route_id']}"
                ),
                "route_id": row["route_id"],
                "target_window_start": row["coverage_window_start"],
                "target_window_end": row["coverage_window_end"],
                "feasibility_status": (
                    "pass_context_available_not_classifier"
                    if passed
                    else "fail_closed_source_shape_or_provenance"
                ),
                "fail_closed_label": "" if passed else source["fail_closed_label"],
                "required_next_action": (
                    "use_as_context_only"
                    if passed
                    else "resolve_selected_column_coverage_units_method_tier_and_same_quarter_D"
                ),
                "allowed_use": "historical_extension_planning_context",
                "blocked_use": "selected_historical_n;final_classifier",
                "claim_boundary": "historical_extension_fail_closed_until_all_gates",
            }
        )
    return rows


def historical_numerator_panel_rows(
    *,
    historical_provisional_dir: str | Path = DEFAULT_HISTORICAL_PROVISIONAL_DIR,
) -> list[dict[str, str]]:
    """Return base-case implemented historical numerator context rows."""

    path = Path(historical_provisional_dir) / "ratewall_historical_provisional_numerator_ledger.csv"
    rows = [
        row
        for row in _read_required(path)
        if row.get("assumption_case") == "base"
    ]
    out = []
    for row in rows:
        context_n = Decimal(row["tdc_ex_overlap_support_bil"]) + Decimal(
            row["public_interest_net_block_partial_bil"]
        )
        out.append(
            {
                "historical_numerator_panel_row_id": (
                    f"historical_numerator_panel::{row['period']}::base"
                ),
                "period": row["period"],
                "assumption_case": "base",
                "tdc_ex_overlap_support_bil": row["tdc_ex_overlap_support_bil"],
                "public_interest_net_block_partial_bil": row[
                    "public_interest_net_block_partial_bil"
                ],
                "direct_treasury_interest_decomposition_bil": row[
                    "direct_treasury_interest_support_bil"
                ],
                "historical_n_context_bil": str(context_n),
                "historical_n_formula": (
                    "tdc_ex_overlap_support_bil + public_interest_net_block_partial_bil"
                ),
                "selected_historical_n_includes_tdc": "false",
                "classifier_allowed": "false",
                "source_status": row["numerator_source_status"],
                "allowed_use": "historical_numerator_context_panel",
                "blocked_use": "final_classifier;direct_treasury_third_additive_term",
                "claim_boundary": "historical_numerator_context_not_selected_n",
            }
        )
    validate_historical_numerator_panel(out)
    return out


def historical_tdc_mechanism_panel_rows(
    *,
    numerator_rows: Sequence[Mapping[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Return TDC mechanism context rows from the implemented numerator panel."""

    rows = list(numerator_rows) if numerator_rows is not None else (
        historical_numerator_panel_rows()
    )
    validate_historical_numerator_panel(rows)
    out = [
        {
            "historical_tdc_mechanism_panel_row_id": (
                f"historical_tdc_mechanism::{row['period']}::{row['assumption_case']}"
            ),
            "period": row["period"],
            "assumption_case": row["assumption_case"],
            "tdc_ex_overlap_support_bil": row["tdc_ex_overlap_support_bil"],
            "public_interest_net_block_partial_bil": row[
                "public_interest_net_block_partial_bil"
            ],
            "tdc_source_basis_chosen": "implemented_historical_provisional_outputs",
            "beta_policy": "normal_forward_constant_beta_context_only",
            "chi_policy": "selected_chi_context_only",
            "tdc_centrality": "diagnostic_context",
            "selected_historical_n_includes_tdc": "false",
            "classifier_allowed": "false",
            "post_2025q4_tdc_source_update_status": (
                "blocked_no_post_2025q4_tdc_source_backed_update"
                if row["period"] > "2025Q4"
                else "not_applicable_pre_2026"
            ),
            "allowed_use": "historical_tdc_mechanism_context",
            "blocked_use": "selected_historical_n;final_classifier;post_2025q4_extension",
            "claim_boundary": "historical_tdc_context_not_classifier",
        }
        for row in rows
    ]
    validate_historical_tdc_mechanism_panel(out)
    return out


def historical_extension_readout_markdown(
    *,
    coverage_rows: Sequence[Mapping[str, str]],
    feasibility_rows: Sequence[Mapping[str, str]],
) -> str:
    """Return compact T3 readout."""

    validate_historical_coverage_contract(coverage_rows)
    return "\n".join(
        [
            "# Historical Coverage Contract",
            "",
            "Historical remains context and validation, not a final wall-hit classifier.",
            "",
            "Implemented panel: `2021Q4-2026Q2`.",
            "Main long-history, strict modern, and 1990 appendix routes are source-shape gates.",
            "Historical TDC is mechanism context; selected_historical_n_includes_tdc=false.",
            "",
            "Formula lock:",
            "",
            "`historical_N_context_bil = tdc_ex_overlap_support_bil + public_interest_net_block_partial_bil`",
            "",
            "Direct Treasury interest is inside the public-interest context block, not a third additive term.",
            "",
            f"Route rows: `{len(coverage_rows)}`; feasibility rows: `{len(feasibility_rows)}`.",
            "",
        ]
    )


def write_historical_coverage_contract_outputs(
    output_dir: str | Path,
    *,
    source_registry_rows: Sequence[Mapping[str, str]],
    coverage_rows: Sequence[Mapping[str, str]],
    feasibility_rows: Sequence[Mapping[str, str]],
    numerator_panel_rows: Sequence[Mapping[str, str]],
    tdc_mechanism_panel_rows: Sequence[Mapping[str, str]],
    readout_markdown: str,
) -> dict[str, Path]:
    """Write T3 historical coverage outputs."""

    validate_historical_tdc_source_registry(source_registry_rows)
    validate_historical_coverage_contract(coverage_rows)
    validate_historical_numerator_panel(numerator_panel_rows)
    validate_historical_tdc_mechanism_panel(tdc_mechanism_panel_rows)
    root = Path(output_dir)
    outputs = {
        "source_registry_csv": root / "ratewall_historical_tdc_source_registry.csv",
        "coverage_contract_csv": root / "ratewall_historical_coverage_contract.csv",
        "extension_feasibility_csv": (
            root / "ratewall_historical_extension_feasibility.csv"
        ),
        "numerator_panel_csv": root / "ratewall_historical_numerator_panel.csv",
        "tdc_mechanism_panel_csv": root / "ratewall_historical_tdc_mechanism_panel.csv",
        "readout_md": root / "historical_extension_readout.md",
    }
    write_rows(
        outputs["source_registry_csv"],
        list(source_registry_rows),
        [
            "tdc_source_registry_row_id",
            "route_id",
            "route_role",
            "expected_window_start",
            "expected_window_end",
            "upstream_path",
            "upstream_selected_column",
            "upstream_file_status",
            "upstream_column_status",
            "upstream_selected_column_nonnull_start",
            "upstream_selected_column_nonnull_end",
            "downstream_path",
            "downstream_selected_column",
            "downstream_file_status",
            "downstream_column_status",
            "downstream_selected_column_nonnull_start",
            "downstream_selected_column_nonnull_end",
            "tdc_source_basis_chosen",
            "selected_column_coverage_status",
            "method_tier_status",
            "unit_basis",
            "route_status",
            "fail_closed_label",
            "allowed_use",
            "blocked_use",
            "claim_boundary",
        ],
    )
    write_rows(
        outputs["coverage_contract_csv"],
        list(coverage_rows),
        HISTORICAL_COVERAGE_CONTRACT_FIELDS,
    )
    write_rows(
        outputs["extension_feasibility_csv"],
        list(feasibility_rows),
        HISTORICAL_EXTENSION_FEASIBILITY_FIELDS,
    )
    write_rows(
        outputs["numerator_panel_csv"],
        list(numerator_panel_rows),
        HISTORICAL_NUMERATOR_PANEL_FIELDS,
    )
    write_rows(
        outputs["tdc_mechanism_panel_csv"],
        list(tdc_mechanism_panel_rows),
        HISTORICAL_TDC_MECHANISM_PANEL_FIELDS,
    )
    outputs["readout_md"].parent.mkdir(parents=True, exist_ok=True)
    outputs["readout_md"].write_text(readout_markdown, encoding="utf-8")
    return outputs


def validate_historical_coverage_contract(
    rows: Sequence[Mapping[str, str]],
) -> None:
    """Validate route-level T3 coverage rows."""

    if not rows:
        raise HistoricalCoverageContractError("coverage contract is empty")
    required = {
        "implemented_short_panel",
        "main_long_history_bank_scope",
        "strict_modern_bank_scope",
        "level_splice_1990_appendix",
    }
    by_route = {row["route_id"]: row for row in rows}
    missing = required - set(by_route)
    if missing:
        raise HistoricalCoverageContractError(f"missing coverage routes: {missing}")
    for row in rows:
        if row["selected_historical_n_includes_tdc"] != "false":
            raise HistoricalCoverageContractError(
                f"historical TDC selected inclusion forbidden: {row['route_id']}"
            )
        if row["classifier_allowed"] != "false":
            raise HistoricalCoverageContractError(
                f"historical classifier forbidden: {row['route_id']}"
            )
        if row["coverage_window_end"] > "2025Q4" and row[
            "route_id"
        ] != "implemented_short_panel":
            raise HistoricalCoverageContractError(
                f"unbacked post-2025Q4 TDC route: {row['route_id']}"
            )
        if "direct_treasury" in row["historical_n_formula"]:
            raise HistoricalCoverageContractError(
                "historical formula double-counts direct Treasury"
            )
        if "direct_treasury" in row["historical_n_additive_terms"]:
            raise HistoricalCoverageContractError(
                "direct Treasury cannot be additive historical N"
            )


def validate_historical_numerator_panel(
    rows: Sequence[Mapping[str, str]],
) -> None:
    """Validate implemented historical numerator panel rows."""

    if not rows:
        raise HistoricalCoverageContractError("historical numerator panel is empty")
    for row in rows:
        if row["selected_historical_n_includes_tdc"] != "false":
            raise HistoricalCoverageContractError("historical selected TDC forbidden")
        if row["classifier_allowed"] != "false":
            raise HistoricalCoverageContractError("historical classifier forbidden")
        expected = Decimal(row["tdc_ex_overlap_support_bil"]) + Decimal(
            row["public_interest_net_block_partial_bil"]
        )
        if Decimal(row["historical_n_context_bil"]) != expected:
            raise HistoricalCoverageContractError("historical N formula mismatch")
        if "direct_treasury" in row["historical_n_formula"]:
            raise HistoricalCoverageContractError("direct Treasury double count")


def validate_historical_tdc_mechanism_panel(
    rows: Sequence[Mapping[str, str]],
) -> None:
    """Validate TDC mechanism rows."""

    if not rows:
        raise HistoricalCoverageContractError("historical TDC mechanism panel is empty")
    for row in rows:
        if row["selected_historical_n_includes_tdc"] != "false":
            raise HistoricalCoverageContractError("historical selected TDC forbidden")
        if row["classifier_allowed"] != "false":
            raise HistoricalCoverageContractError("historical classifier forbidden")
        if row["period"] > "2025Q4" and not row[
            "post_2025q4_tdc_source_update_status"
        ].startswith("blocked"):
            raise HistoricalCoverageContractError("post-2025Q4 TDC unbacked")


def _implemented_bounds(
    historical_provisional_dir: str | Path,
) -> tuple[tuple[str, str], tuple[str, str]]:
    root = Path(historical_provisional_dir)
    numerator = [
        row["period"]
        for row in _read_required(root / "ratewall_historical_provisional_numerator_ledger.csv")
        if row.get("assumption_case") == "base"
    ]
    denominator = [
        row["period"]
        for row in _read_required(root / "ratewall_historical_provisional_denominator_panel.csv")
    ]
    return (min(numerator), max(numerator)), (min(denominator), max(denominator))


def _read_required(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise HistoricalCoverageContractError(f"missing required input: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
