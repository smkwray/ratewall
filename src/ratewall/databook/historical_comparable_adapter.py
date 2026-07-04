"""Historical comparable adapter for RateWall model surfaces.

This module keeps historical rows useful for comparison without promoting them
into classifiers or filling missing channel values from forecast assumptions.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path

from ratewall.databook.table_io import write_rows

DEFAULT_METHODOLOGY_PARITY_DIR = Path(
    "var/preliminary_scenario_results/methodology_parity"
)
DEFAULT_HISTORICAL_CLEAN_PATH = Path(
    "outputs/tables/ratewall_historical_closest_approach_clean.csv"
)

HISTORICAL_CHANNEL_ADAPTER_STATUS_FIELDS = [
    "historical_channel_adapter_status_row_id",
    "surface_id",
    "channel_id",
    "channel_label",
    "shared_channel_family",
    "historical_adapter_status",
    "historical_source_column",
    "historical_source_row_count",
    "historical_numerator_value_bil",
    "historical_ratio_not_classifier",
    "source_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

HISTORICAL_COMPARABLE_SURFACE_FIELDS = [
    "historical_comparable_surface_row_id",
    "historical_period_id",
    "period",
    "quarter",
    "assumption_case",
    "ratio_object_id",
    "channel_id",
    "shared_channel_family",
    "historical_numerator_value_bil",
    "historical_denominator_variant",
    "historical_path_D_bil",
    "fixed_D_comparison_bil",
    "historical_rate_gap_pct_points",
    "historical_ratio",
    "historical_ratio_not_classifier",
    "source_status",
    "adapter_status",
    "source_historical_row_id",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

HISTORICAL_DENOMINATOR_VARIANT_BRIDGE_FIELDS = [
    "historical_denominator_variant_bridge_row_id",
    "surface_id",
    "denominator_variant",
    "denominator_object_id",
    "denominator_role",
    "fixed_anchor_component_pp_gdp",
    "historical_path_D_bil",
    "fixed_D_comparison_bil",
    "moving_D_bil",
    "historical_rate_gap_pct_points",
    "selected_variant",
    "variant_role",
    "historical_ratio_not_classifier",
    "source_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


class HistoricalComparableAdapterError(ValueError):
    """Raised when historical comparable adapter inputs are inconsistent."""


EXPLICIT_HISTORICAL_COMPONENT_COLUMNS = {
    "tdc_ex_overlap_current_demand_support": "tdc_current_demand_support_bil",
    "direct_treasury_interest_support": "direct_interest_support_bil",
}

PUBLIC_INTEREST_CHANNELS = {
    "direct_treasury_interest_support",
    "bank_treasury_interest_support",
    "net_interest_after_fiscal_tga_offsets",
    "current_remittance_demand_offset",
    "future_remittance_drag_demand_offset",
    "iorb_recipient_demand_channel",
    "on_rrp_recipient_demand_channel",
    "fiscal_offset",
    "tga_liquidity_offset",
    "foreign_treasury_holder_leakage_drag",
    "interest_income_tax_timing_drag",
}

RESIDUAL_CHANNELS = {
    "firm_cash_attenuation",
    "safe_asset_allocation_offset",
    "safe_asset_allocation_drag",
    "zero_interest_credit_attenuation",
    "household_safe_yield_capture",
    "deposit_mmf_substitution_offset",
    "deposit_mmf_substitution_drag",
    "firm_liquid_asset_cushion",
    "firm_rollover_pressure_drag",
}


def historical_channel_adapter_status_rows(
    *,
    methodology_parity_dir: str | Path = DEFAULT_METHODOLOGY_PARITY_DIR,
    historical_clean_path: str | Path = DEFAULT_HISTORICAL_CLEAN_PATH,
) -> list[dict[str, str]]:
    """Return one historical adapter status row for each shared channel."""

    parity_rows = _historical_parity_channel_rows(Path(methodology_parity_dir))
    historical_rows = _read_required(Path(historical_clean_path))
    historical_fields = set(historical_rows[0]) if historical_rows else set()
    out: list[dict[str, str]] = []
    for row in parity_rows:
        channel_id = row["channel_id"]
        source_column = EXPLICIT_HISTORICAL_COMPONENT_COLUMNS.get(channel_id, "")
        source_row_count = (
            _nonempty_count(historical_rows, source_column)
            if source_column in historical_fields
            else 0
        )
        out.append(
            {
                "historical_channel_adapter_status_row_id": (
                    f"historical_channel_adapter_status::{channel_id}"
                ),
                "surface_id": row["surface_id"],
                "channel_id": channel_id,
                "channel_label": row["channel_label"],
                "shared_channel_family": _shared_channel_family(channel_id),
                "historical_adapter_status": _adapter_status(
                    row=row,
                    source_column=source_column,
                    source_row_count=source_row_count,
                ),
                "historical_source_column": source_column,
                "historical_source_row_count": str(source_row_count),
                "historical_numerator_value_bil": "",
                "historical_ratio_not_classifier": "true",
                "source_status": _source_status(
                    row=row,
                    source_column=source_column,
                    source_row_count=source_row_count,
                ),
                "allowed_use": "historical_comparable_adapter_context_only",
                "blocked_use": (
                    "canonical_headline_promotion;evidence_mode_claim;"
                    "forecast_assumption_backfill;historical_classifier"
                ),
                "claim_boundary": "historical_context_not_classifier_no_n_or_d_change",
            }
        )
    return out


def historical_comparable_surface_rows(
    *,
    methodology_parity_dir: str | Path = DEFAULT_METHODOLOGY_PARITY_DIR,
    historical_clean_path: str | Path = DEFAULT_HISTORICAL_CLEAN_PATH,
) -> list[dict[str, str]]:
    """Return source-backed historical component rows on shared channel ids."""

    status_by_channel = {
        row["channel_id"]: row
        for row in historical_channel_adapter_status_rows(
            methodology_parity_dir=methodology_parity_dir,
            historical_clean_path=historical_clean_path,
        )
    }
    historical_rows = _read_required(Path(historical_clean_path))
    out: list[dict[str, str]] = []
    for source_row in historical_rows:
        _assert_historical_clean_row_is_noncanonical(source_row)
        for channel_id, source_column in EXPLICIT_HISTORICAL_COMPONENT_COLUMNS.items():
            if source_column not in source_row or source_row[source_column] == "":
                continue
            status_row = status_by_channel[channel_id]
            if not status_row["source_status"].startswith("source_backed"):
                continue
            out.append(
                {
                    "historical_comparable_surface_row_id": (
                        "historical_comparable_surface::"
                        f"{source_row['period']}::{source_row['assumption_case']}::"
                        f"{channel_id}"
                    ),
                    "historical_period_id": source_row["period"],
                    "period": source_row["period"],
                    "quarter": source_row["quarter"],
                    "assumption_case": source_row["assumption_case"],
                    "ratio_object_id": source_row["ratio_object_id"],
                    "channel_id": channel_id,
                    "shared_channel_family": status_row["shared_channel_family"],
                    "historical_numerator_value_bil": source_row[source_column],
                    "historical_denominator_variant": (
                        "historical_path_denominator_v1_required"
                    ),
                    "historical_path_D_bil": "",
                    "fixed_D_comparison_bil": "",
                    "historical_rate_gap_pct_points": "",
                    "historical_ratio": source_row["ratewall_ratio"],
                    "historical_ratio_not_classifier": "true",
                    "source_status": (
                        f"source_backed_noncanonical_historical_column::{source_column}"
                    ),
                    "adapter_status": status_row["historical_adapter_status"],
                    "source_historical_row_id": source_row[
                        "historical_closest_approach_clean_row_id"
                    ],
                    "allowed_use": "historical_component_comparison_context_only",
                    "blocked_use": (
                        "canonical_headline_promotion;evidence_mode_claim;"
                        "historical_classifier;forecast_assumption_backfill"
                    ),
                    "claim_boundary": (
                        "historical_component_context_from_noncanonical_clean_path"
                    ),
                }
            )
    return out


def historical_denominator_variant_bridge_rows(
    *,
    methodology_parity_dir: str | Path = DEFAULT_METHODOLOGY_PARITY_DIR,
) -> list[dict[str, str]]:
    """Return historical denominator variant labels without changing D."""

    denominator_rows = _read_required(
        Path(methodology_parity_dir) / "ratewall_methodology_parity_denominators.csv"
    )
    historical = _single_row(
        denominator_rows,
        key="surface_id",
        value="historical_path_context",
        label="historical methodology parity denominator row",
    )
    fixed_anchor = historical["fixed_anchor_component"]
    common = {
        "surface_id": "historical_path_context",
        "historical_ratio_not_classifier": "true",
        "allowed_use": "historical_denominator_comparison_context_only",
        "blocked_use": (
            "silent_fixed_D_reuse_as_historical_primary;"
            "scenario_moving_D_reinterpretation;canonical_headline_promotion"
        ),
        "claim_boundary": "historical_denominator_variant_labels_no_D_change",
    }
    return [
        {
            **common,
            "historical_denominator_variant_bridge_row_id": (
                "historical_denominator_variant_bridge::fixed_D_comparison"
            ),
            "denominator_variant": "fixed_D_comparison",
            "denominator_object_id": "literature_annual_flow_bridge_candidate",
            "denominator_role": "comparison_lane_not_primary_historical",
            "fixed_anchor_component_pp_gdp": fixed_anchor,
            "historical_path_D_bil": "",
            "fixed_D_comparison_bil": "",
            "moving_D_bil": "",
            "historical_rate_gap_pct_points": "",
            "selected_variant": "false",
            "variant_role": "comparison_only",
            "source_status": "source_backed_fixed_anchor_component_not_bil_D",
        },
        {
            **common,
            "historical_denominator_variant_bridge_row_id": (
                "historical_denominator_variant_bridge::historical_path_D"
            ),
            "denominator_variant": "historical_path_D",
            "denominator_object_id": historical["denominator_object_id"],
            "denominator_role": historical["denominator_role"],
            "fixed_anchor_component_pp_gdp": fixed_anchor,
            "historical_path_D_bil": "",
            "fixed_D_comparison_bil": "",
            "moving_D_bil": "",
            "historical_rate_gap_pct_points": "",
            "selected_variant": "true",
            "variant_role": "historical_context_primary",
            "source_status": "source_backed_historical_denominator_contract_no_bil_export",
        },
        {
            **common,
            "historical_denominator_variant_bridge_row_id": (
                "historical_denominator_variant_bridge::moving_D_not_applicable"
            ),
            "denominator_variant": "moving_D_not_applicable",
            "denominator_object_id": "",
            "denominator_role": "not_a_historical_scenario_response",
            "fixed_anchor_component_pp_gdp": "",
            "historical_path_D_bil": "",
            "fixed_D_comparison_bil": "",
            "moving_D_bil": "",
            "historical_rate_gap_pct_points": "",
            "selected_variant": "false",
            "variant_role": "not_applicable_to_historical_context",
            "source_status": "not_applicable_historical_rate_path_is_not_forecast_scenario",
        },
    ]


def write_historical_comparable_adapter_outputs(
    output_dir: str | Path,
    *,
    status_rows: Sequence[Mapping[str, str]],
    surface_rows: Sequence[Mapping[str, str]],
    denominator_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    """Write historical comparable adapter CSV outputs."""

    root = Path(output_dir)
    outputs = {
        "status_csv": root / "ratewall_historical_channel_adapter_status.csv",
        "surface_csv": root / "ratewall_historical_comparable_surface.csv",
        "denominator_csv": (
            root / "ratewall_historical_denominator_variant_bridge.csv"
        ),
    }
    write_rows(
        outputs["status_csv"],
        list(status_rows),
        HISTORICAL_CHANNEL_ADAPTER_STATUS_FIELDS,
    )
    write_rows(
        outputs["surface_csv"],
        list(surface_rows),
        HISTORICAL_COMPARABLE_SURFACE_FIELDS,
    )
    write_rows(
        outputs["denominator_csv"],
        list(denominator_rows),
        HISTORICAL_DENOMINATOR_VARIANT_BRIDGE_FIELDS,
    )
    return outputs


def _historical_parity_channel_rows(root: Path) -> list[dict[str, str]]:
    rows = _read_required(root / "ratewall_methodology_parity_channels.csv")
    out = [row for row in rows if row["surface_id"] == "historical_path_context"]
    if not out:
        raise HistoricalComparableAdapterError(
            "missing historical_path_context channel rows"
        )
    return out


def _adapter_status(
    *,
    row: Mapping[str, str],
    source_column: str,
    source_row_count: int,
) -> str:
    if source_column and source_row_count:
        if row["centrality"] == "not_ready":
            return "source_backed_legacy_component_not_final_parity"
        return "source_backed_component_context_not_classifier"
    if row["centrality"] == "context":
        return "context_only_no_explicit_component_column"
    return "gap_no_source_backed_historical_component"


def _source_status(
    *,
    row: Mapping[str, str],
    source_column: str,
    source_row_count: int,
) -> str:
    if source_column and source_row_count:
        return f"source_backed_noncanonical_historical_column::{source_column}"
    if row["centrality"] == "context":
        return "historical_context_available_but_no_component_column_in_adapter"
    return "not_source_backed_in_current_adapter"


def _shared_channel_family(channel_id: str) -> str:
    if channel_id == "tdc_ex_overlap_current_demand_support":
        return "tdc_ex_overlap_support"
    if channel_id in PUBLIC_INTEREST_CHANNELS:
        return "public_interest_net_block"
    if channel_id in RESIDUAL_CHANNELS:
        return "residual_replacement_channel"
    return "unclassified_channel_family"


def _assert_historical_clean_row_is_noncanonical(row: Mapping[str, str]) -> None:
    guards = {
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
    }
    for field, expected in guards.items():
        if row.get(field) != expected:
            raise HistoricalComparableAdapterError(
                f"historical source row {row.get('historical_closest_approach_clean_row_id')} "
                f"has {field}={row.get(field)!r}; expected {expected!r}"
            )


def _single_row(
    rows: Sequence[Mapping[str, str]], *, key: str, value: str, label: str
) -> Mapping[str, str]:
    matches = [row for row in rows if row[key] == value]
    if len(matches) != 1:
        raise HistoricalComparableAdapterError(
            f"expected one {label}; found {len(matches)}"
        )
    return matches[0]


def _nonempty_count(rows: Sequence[Mapping[str, str]], column: str) -> int:
    return sum(1 for row in rows if row.get(column) not in ("", None))


def _read_required(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise HistoricalComparableAdapterError(f"missing required input: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
