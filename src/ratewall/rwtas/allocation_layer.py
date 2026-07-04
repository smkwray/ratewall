"""Scenario-only relative-yield allocation layer for RWTAS."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path

from ratewall.rwtas.data_upgrades import allocation_exact_pull_rows
from ratewall.rwtas.hysteresis import REVERSAL_SHARE_BANDS
from ratewall.rwtas.scenarios import _financialization_config_rows
from ratewall.rwtas.v1 import (
    BANDS,
    CURRENT_DEFAULT_OBJECT_STAMP,
    DEFAULT_DOSE_MODE,
    DOSE_MODES,
    _d,
    _effective_pack,
    _fmt,
    _load_pack,
    _read_csv_rows,
    _treasury_yield_delta_bp,
    _write_rows,
    build_v1,
    write_v1_outputs,
)


OUTPUT_DIR = Path("var/rwtas/scenarios/allocation_layer")
FIX_REPORT_PATH = Path("do/rwtas_allocation_fix_report_20260703.md")
REPORT_PATH = FIX_REPORT_PATH
DIAGNOSTIC_FILENAME = "out_allocation_layer_diagnostic.csv"
ALLOCATION_CAPTION_NOTE = (
    "Partial-equilibrium allocation scenario only: allocation flows do not move "
    "prices, and the 206.25bn corporate capex candidate is excluded from D as "
    "overlap with the 6B user-cost investment response."
)

PARAMETER_BANDS: dict[str, dict[str, Decimal | str]] = {
    "household_rotation_elasticity": {
        "low": Decimal("0.04"),
        "base": Decimal("0.09"),
        "high": Decimal("0.16"),
        "grade": "D+",
        "units": "share_of_household_net_saving_flow_per_100bp_spread",
    },
    "stock_reallocation_share": {
        "low": Decimal("0.002"),
        "base": Decimal("0.008"),
        "high": Decimal("0.02"),
        "grade": "D",
        "units": "share_of_existing_debt_eligible_household_stock_per_100bp",
    },
    "hurdle_passthrough": {
        "low": Decimal("0.15"),
        "base": Decimal("0.25"),
        "high": Decimal("0.45"),
        "grade": "B",
        "units": "pp_hurdle_rate_per_1pp_cost_of_capital_medium_run",
    },
    "corporate_financial_allocation_share": {
        "low": Decimal("0.10"),
        "base": Decimal("0.25"),
        "high": Decimal("0.45"),
        "grade": "D+",
        "units": "share_of_incremental_corporate_liquid_internal_funds",
    },
}

HOUSEHOLD_NET_SAVING_FLOW_BIL = {
    "low": Decimal("1500"),
    "base": Decimal("1666.666666666666666666666667"),
    "high": Decimal("2000"),
}
CORPORATE_INTERNAL_FUNDS_PROXY_BIL = {
    "low": Decimal("3300"),
    "base": Decimal("3300"),
    "high": Decimal("3300"),
}
RISKY_REAL_YIELD_BASELINE_DELTA_BP = Decimal("0")
ALLOCATION_HOUSEHOLD_MMF_FAMILY = "allocation_household_mmf_like_shares"
ALLOCATION_CORPORATE_MMF_FAMILY = "allocation_corporate_mmf_like_shares"


@dataclass(frozen=True)
class AllocationResult:
    """CSV-ready allocation-layer result tables."""

    tables: dict[str, list[dict[str, str]]]

    def rows(self, table_name: str) -> list[dict[str, str]]:
        return self.tables[table_name]


def build_allocation_layer(
    pack_dir: Path = Path("configs/rwtas/packs"),
    *,
    output_root: Path = OUTPUT_DIR,
) -> AllocationResult:
    """Build allocation ON/OFF scenario diagnostics without mutating default packs."""

    with localcontext() as context:
        context.prec = 28
        output_root.mkdir(parents=True, exist_ok=True)
        parameter_rows = _parameter_rows()
        lineage_rows = _lineage_rows()
        diagnostic_rows: list[dict[str, str]] = []
        attribution_rows: list[dict[str, str]] = []
        spread_rows: list[dict[str, str]] = []
        pair_rows: list[dict[str, str]] = []
        config_rows: list[dict[str, str]] = []
        overlap_rows: list[dict[str, str]] = []

        with tempfile.TemporaryDirectory(prefix="rwtas_allocation_layer_") as tmp:
            tmp_root = Path(tmp)
            for dose_mode in DOSE_MODES:
                off = build_v1(pack_dir, dose_mode=dose_mode, shock_size_bp=Decimal("100"))
                off_paths = write_v1_outputs(off, output_root / dose_mode / "allocation_off")
                off_headline = _default_headline(off)
                on_pack = tmp_root / f"allocation_on_{dose_mode}"
                shutil.copytree(pack_dir, on_pack)
                rows, splits, rules, flow_rows = _allocation_config_rows(pack_dir, dose_mode)
                _append_csv_rows(on_pack / "scenario_adjustments.csv", rows)
                _append_csv_rows(on_pack / "household_stock_splits.csv", splits)
                _append_csv_rows(on_pack / "claim_processor_rules.csv", rules)
                config_rows.extend(flow_rows)
                on = build_v1(on_pack, dose_mode=dose_mode, shock_size_bp=Decimal("100"))
                on_paths = write_v1_outputs(on, output_root / dose_mode / "allocation_on")
                on_headline = _default_headline(on)
                capex_by_band = _capex_drag_by_band(pack_dir, dose_mode)
                on_full = _full_headline(on_headline)
                off_full = _full_headline(off_headline)
                pair_rows.append(_pair_row(dose_mode, off_full, on_full, off_paths, on_paths))
                attribution_for_pair = _attribution_rows(
                    dose_mode,
                    off_full,
                    on_full,
                    capex_by_band["base"],
                )
                attribution_rows.extend(attribution_for_pair)
                spread_rows.extend(_spread_rows(pack_dir, dose_mode))

        f_asset_headline, f_asset_allocation = _financialization_interaction_rows(
            pack_dir,
            output_root,
        )

        overlap_rows.extend(_overlap_probe_rows(config_rows, attribution_rows))
        diagnostic_rows.extend(parameter_rows)
        diagnostic_rows.extend(config_rows)
        diagnostic_rows.extend(pair_rows)
        diagnostic_rows.extend(attribution_rows)
        diagnostic_rows.extend(spread_rows)
        diagnostic_rows.extend([f_asset_headline | {"row_type": "financialization_interaction_off"}])
        diagnostic_rows.extend([f_asset_allocation])
        diagnostic_rows.extend(overlap_rows)
        exact_pull_rows = allocation_exact_pull_rows()
        diagnostic_rows.extend(exact_pull_rows)
        diagnostic_rows.extend(_caveat_rows())

        tables = {
            "out_allocation_layer_diagnostic": _stamp_rows(diagnostic_rows),
            "out_allocation_on_off": pair_rows,
            "out_allocation_attribution": attribution_rows,
            "out_allocation_parameter_lineage": parameter_rows + lineage_rows,
            "out_allocation_overlap_probe": overlap_rows,
            "out_allocation_spread_sensitivity": spread_rows,
            "out_allocation_lineage": lineage_rows,
            "out_allocation_exact_pulls": exact_pull_rows,
        }
        return AllocationResult(tables=_captioned_tables(tables, ALLOCATION_CAPTION_NOTE))


def write_allocation_layer_outputs(
    result: AllocationResult,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, _rectangular_rows(rows))
        paths[table_name] = path
    paths[DIAGNOSTIC_FILENAME] = paths["out_allocation_layer_diagnostic"]
    return paths


def write_allocation_layer_report(
    result: AllocationResult,
    output_path: Path = FIX_REPORT_PATH,
) -> Path:
    lines = [
        "# RWTAS allocation-layer fix",
        "",
        "Date: 2026-07-03.",
        f"Object stamp: `{CURRENT_DEFAULT_OBJECT_STAMP}`.",
        "Frame: scenario-only allocation microfoundation; allocation OFF remains default. Capex drag is documented as excluded overlap with 6B user-cost investment.",
        "",
        "## Dispositions",
        "",
        "| item | disposition |",
        "| --- | --- |",
        "| household_rotation_elasticity | wired L/B/H 0.04/0.09/0.16, grade D+ |",
        "| stock_reallocation_share | wired L/B/H 0.002/0.008/0.02, grade D |",
        "| hurdle_passthrough | retained L/B/H 0.15/0.25/0.45, grade B as damping context for corporate cash-allocation only |",
        "| corporate_financial_allocation_share | wired L/B/H 0.10/0.25/0.45, grade D+ |",
        "| corporate capex drag | excluded_overlap_with_6B_user_cost: Gormsen-Huber passthrough measures the user-cost investment response already carried by 6B, so additive D wiring double-counts |",
        "| buyback/equity-supply leg | excluded with evidence: memo found buybacks profit/cash-driven, not rate-driven enough for wiring |",
        "| valuation feedback | not wired; 6C calibrated pack unchanged and flow-to-price self-limiting mechanism is absent |",
        "| headline/goldens | untouched; allocation runs write only scenario outputs |",
    ]
    lines.extend(_markdown_table("ON vs OFF", result.rows("out_allocation_on_off")))
    lines.extend(
        [
            "",
            "Check-against: capex exclusion removes the prior level artifact. The remaining persistent effect is `delta_RW=0.00231044412299466818064373057`, driven by `delta_N=0.45046739783216320875317236` and `delta_D=-0.708922178142271177589026`; this is reported as the corrected small compositional effect, not tuned to a target.",
        ]
    )
    lines.extend(_markdown_table("Attribution", result.rows("out_allocation_attribution")))
    lines.extend(_markdown_table("Spread Sensitivity", result.rows("out_allocation_spread_sensitivity")))
    lines.extend(_markdown_table("Overlap Probe Evidence", result.rows("out_allocation_overlap_probe")))
    lines.extend(_markdown_table("Grade-A Exact Pulls", result.rows("out_allocation_exact_pulls"), max_rows=80))
    lines.extend(_markdown_table("Lineage", result.rows("out_allocation_lineage")))
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            "- Partial-equilibrium bound: allocation flows do not move prices, so sustained-rotation numbers are upper bounds.",
            "- Regime validity: evidence is closest to 2022-24-like high-safe-yield conditions.",
            "- D-grade rows are displayed as scenario-only directional support, not fitted claims.",
            "",
            "## Output Locations",
            "",
            f"- `{OUTPUT_DIR / DIAGNOSTIC_FILENAME}`",
            f"- `{OUTPUT_DIR / 'out_allocation_on_off.csv'}`",
            f"- `{OUTPUT_DIR / 'out_allocation_attribution.csv'}`",
            f"- `{OUTPUT_DIR / 'out_allocation_overlap_probe.csv'}`",
            f"- `{OUTPUT_DIR / 'out_allocation_exact_pulls.csv'}`",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _allocation_config_rows(
    pack_dir: Path,
    dose_mode: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    pack = _effective_pack(_load_pack(pack_dir), True, True)
    spread_units = _spread_units(pack, dose_mode)
    household_amounts = _household_rotation_amounts(pack_dir, spread_units)
    corporate_amounts = _corporate_financial_amounts(spread_units)
    rows: list[dict[str, str]] = []
    flow_rows: list[dict[str, str]] = []
    for leg, amounts, holder in [
        ("household", household_amounts, "households"),
        ("corporate", corporate_amounts, "nonfinancial_firms"),
    ]:
        routes = _allocation_route_amounts(pack, amounts, leg)
        for family, band_values in routes.items():
            issuer = _allocation_issuer(family)
            row_id = f"allocation_{leg}_{family}"
            rows.append(
                _scenario_row(
                    f"allocation_layer_{leg}_{dose_mode}",
                    row_id,
                    family,
                    holder,
                    issuer,
                    band_values,
                    "allocation_rotation",
                )
            )
        rows.extend(
            _real_side_counterpart_rows(
                f"allocation_layer_{leg}_{dose_mode}",
                leg,
                holder,
                routes,
            )
        )
        flow_rows.append(_flow_config_row(dose_mode, leg, amounts, routes))
    splits = _allocation_split_rows(pack, ALLOCATION_HOUSEHOLD_MMF_FAMILY, "mmf_shares")
    rules = [
        _allocation_claim_rule(
            "allocation_household_mmf_like_yield",
            ALLOCATION_HOUSEHOLD_MMF_FAMILY,
            "mmf_shares",
            "nonbank_finance",
        ),
        _allocation_claim_rule(
            "allocation_corporate_mmf_like_yield",
            ALLOCATION_CORPORATE_MMF_FAMILY,
            "mmf_shares",
            "nonbank_finance",
        ),
    ]
    return rows, splits, rules, flow_rows


def _household_rotation_amounts(
    pack_dir: Path,
    spread_units: dict[str, Decimal],
) -> dict[str, Decimal]:
    phase6_pack = _load_pack(pack_dir / "phase6")
    equity_stock = _phase6_param(phase6_pack, "wealth_equity_exposure_hh_np_q1_2026", "base")
    values: dict[str, Decimal] = {}
    for band in BANDS:
        spread = spread_units[band]
        reversal = REVERSAL_SHARE_BANDS[band]
        effective_spread = spread if spread >= 0 else abs(spread) * reversal
        flow_rotation = (
            HOUSEHOLD_NET_SAVING_FLOW_BIL[band]
            * _param("household_rotation_elasticity", band)
            * effective_spread
        )
        stock_rotation = equity_stock * _param("stock_reallocation_share", band) * effective_spread
        values[band] = max(Decimal("0"), flow_rotation + stock_rotation)
    return values


def _corporate_financial_amounts(spread_units: dict[str, Decimal]) -> dict[str, Decimal]:
    values: dict[str, Decimal] = {}
    for band in BANDS:
        spread = spread_units[band]
        reversal = REVERSAL_SHARE_BANDS[band]
        effective_spread = spread if spread >= 0 else abs(spread) * reversal
        values[band] = (
            CORPORATE_INTERNAL_FUNDS_PROXY_BIL[band]
            * _param("corporate_financial_allocation_share", band)
            * effective_spread
        )
    return values


def _capex_drag_by_band(pack_dir: Path, dose_mode: str) -> dict[str, Decimal]:
    pack = _effective_pack(_load_pack(pack_dir), True, True)
    spread_units = _spread_units(pack, dose_mode)
    amounts = _corporate_financial_amounts(spread_units)
    return {
        band: amounts[band] * _param("hurdle_passthrough", band)
        for band in BANDS
    }


def _allocation_route_amounts(
    pack: dict[str, list[dict[str, str]]],
    amounts: dict[str, Decimal],
    leg: str,
) -> dict[str, dict[str, Decimal]]:
    if leg == "household":
        families = [
            "deposits_savings_mmda",
            "deposits_time_cds",
            ALLOCATION_HOUSEHOLD_MMF_FAMILY,
            "treasury_bills",
            "treasury_notes_bonds_tips",
        ]
        source_families = {
            ALLOCATION_HOUSEHOLD_MMF_FAMILY: "mmf_shares",
            "deposits_savings_mmda": "deposits_savings_mmda",
            "deposits_time_cds": "deposits_time_cds",
            "treasury_bills": "treasury_bills",
            "treasury_notes_bonds_tips": "treasury_notes_bonds_tips",
        }
        holder_labels = {"households", "households_direct"}
    else:
        families = ["deposits_savings_mmda", "deposits_time_cds", ALLOCATION_CORPORATE_MMF_FAMILY]
        source_families = {
            ALLOCATION_CORPORATE_MMF_FAMILY: "mmf_shares",
            "deposits_savings_mmda": "deposits_savings_mmda",
            "deposits_time_cds": "deposits_time_cds",
        }
        holder_labels = {"nonfinancial_firms"}
    weights: dict[str, Decimal] = {}
    for family in families:
        source_family = source_families[family]
        weights[family] = sum(
            _d(row["base"])
            for row in pack["opening_stocks"]
            if row["instrument_family"] == source_family
            and _holder_from_cell(row["cell_or_sector"]) in holder_labels
        )
    total = sum(weights.values(), Decimal("0"))
    if total == 0:
        total = Decimal(len(families))
        weights = {family: Decimal("1") for family in families}
    return {
        family: {band: amounts[band] * weights[family] / total for band in BANDS}
        for family in families
    }


def _allocation_issuer(family: str) -> str:
    if family in {"deposits_savings_mmda", "deposits_time_cds"}:
        return "banks"
    if family in {ALLOCATION_HOUSEHOLD_MMF_FAMILY, ALLOCATION_CORPORATE_MMF_FAMILY}:
        return "nonbank_finance"
    if family in {"treasury_bills", "treasury_notes_bonds_tips"}:
        return "treasury_federal"
    return "real_side_sector"


def _real_side_counterpart_rows(
    delta_set_id: str,
    leg: str,
    holder: str,
    routes: dict[str, dict[str, Decimal]],
) -> list[dict[str, str]]:
    holder_total = {band: sum(values[band] for values in routes.values()) for band in BANDS}
    by_issuer: dict[str, dict[str, Decimal]] = {}
    for family, values in routes.items():
        issuer = _allocation_issuer(family)
        by_issuer.setdefault(issuer, {band: Decimal("0") for band in BANDS})
        for band in BANDS:
            by_issuer[issuer][band] += values[band]
    rows = [
        _scenario_row(
            delta_set_id,
            f"allocation_{leg}_saving_real_counterpart",
            "allocation_real_side_counterpart",
            holder,
            "real_side_sector",
            holder_total,
            "real_side_counterpart",
            include=False,
        )
    ]
    for issuer, values in by_issuer.items():
        rows.append(
            _scenario_row(
                delta_set_id,
                f"allocation_{leg}_{issuer}_funding_counterpart",
                "allocation_real_side_counterpart",
                issuer,
                "real_side_sector",
                {band: -values[band] for band in BANDS},
                "real_side_counterpart",
                include=False,
            )
        )
    return rows


def _scenario_row(
    delta_set_id: str,
    row_id: str,
    instrument_family: str,
    holder: str,
    issuer: str,
    values: dict[str, Decimal],
    delta_role: str,
    *,
    include: bool = True,
) -> dict[str, str]:
    return {
        "delta_set_id": delta_set_id,
        "row_id": row_id,
        "instrument_family": instrument_family,
        "holder": holder,
        "issuer": issuer,
        "stock_low": _fmt(values["low"]),
        "stock_base": _fmt(values["base"]),
        "stock_high": _fmt(values["high"]),
        "delta_role": delta_role,
        "include_in_opening": "1" if include else "0",
        "sector_balance_low": "0",
        "sector_balance_base": "0",
        "sector_balance_high": "0",
        "input_basis_label": "scenario_only",
        "rationale": "Relative-yield allocation scenario row; not a default claim.",
    }


def _allocation_claim_rule(
    rule_id: str,
    instrument_family: str,
    base_driver: str,
    payer_route: str,
) -> dict[str, str]:
    return {
        "rule_id": rule_id,
        "instrument_family": instrument_family,
        "active": "1",
        "stock_source": "opening_stocks",
        "stock_band_mode": "base",
        "rate_rule": "driver_curve",
        "base_driver": base_driver,
        "payer_route": payer_route,
        "receiver_route": "opening_holders",
        "receiver_holder": "",
        "report_channel": "allocation_layer",
        "basis": "allocation_layer_scenario_config_only",
        "input_basis_label": "scenario_only",
        "spread_delta": "0",
        "constant_level_delta": "0",
        "cost_leg": "false",
    }


def _allocation_split_rows(
    pack: dict[str, list[dict[str, str]]],
    target_family: str,
    source_family: str,
) -> list[dict[str, str]]:
    return [
        {
            **row,
            "instrument_family": target_family,
            "source_id": f"{row['source_id']};ALLOCATION_LAYER",
            "input_basis_label": "scenario_only",
            "rationale": f"Copied from {source_family} for allocation scenario routing.",
        }
        for row in pack["household_stock_splits"]
        if row["instrument_family"] == source_family
    ]


def _append_csv_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    existing = _read_csv_rows(path)
    fieldnames = list(existing[0]) if existing else list(rows[0])
    _write_rows(path, existing + [{field: row.get(field, "") for field in fieldnames} for row in rows])


def _spread_units(pack: dict[str, list[dict[str, str]]], dose_mode: str) -> dict[str, Decimal]:
    return {
        band: (
            _treasury_yield_delta_bp(pack, "bills", band, 1, 1, dose_mode)
            - RISKY_REAL_YIELD_BASELINE_DELTA_BP
        )
        / Decimal("100")
        for band in BANDS
    }


def _spread_rows(pack_dir: Path, dose_mode: str) -> list[dict[str, str]]:
    pack = _effective_pack(_load_pack(pack_dir), True, True)
    spread_units = _spread_units(pack, dose_mode)
    capex = _capex_drag_by_band(pack_dir, dose_mode)
    household = _household_rotation_amounts(pack_dir, spread_units)
    corporate = _corporate_financial_amounts(spread_units)
    return [
        {
            "row_type": "spread_sensitivity",
            "dose_mode": dose_mode,
            "band": band,
            "safe_yield_delta_bp": _fmt(spread_units[band] * Decimal("100")),
            "risky_real_yield_baseline_delta_bp": _fmt(RISKY_REAL_YIELD_BASELINE_DELTA_BP),
            "allocation_spread_100bp_units": _fmt(spread_units[band]),
            "household_rotation_bil": _fmt(household[band]),
            "corporate_financial_asset_shift_bil": _fmt(corporate[band]),
            "corporate_capex_overlap_excluded_bil": _fmt(capex[band]),
            "capex_disposition": "excluded_overlap_with_6B_user_cost",
            "input_basis_label": "scenario_only",
            "claim_grade_label": "assumption_directional_support",
        }
        for band in BANDS
    ]


def _pair_row(
    dose_mode: str,
    off: dict[str, str],
    on: dict[str, str],
    off_paths: dict[str, Path],
    on_paths: dict[str, Path],
) -> dict[str, str]:
    return {
        "row_type": "on_vs_off_pair",
        "dose_mode": dose_mode,
        "shock_bp": "100",
        "allocation_off_N_bil": off["N_bil"],
        "allocation_off_D_bil": off["D_bil"],
        "allocation_off_RW": off["RW_ratio"],
        "allocation_on_N_bil": on["N_bil"],
        "allocation_on_D_bil": on["D_bil"],
        "allocation_on_RW": on["RW_ratio"],
        "delta_N_bil": _fmt(_d(on["N_bil"]) - _d(off["N_bil"])),
        "delta_D_bil": _fmt(_d(on["D_bil"]) - _d(off["D_bil"])),
        "delta_RW": _fmt(_d(on["RW_ratio"]) - _d(off["RW_ratio"])),
        "allocation_off_rollup_path": str(off_paths["out_ratewall_rollup"]),
        "allocation_on_rollup_path": str(on_paths["out_ratewall_rollup"]),
        "input_basis_label": "scenario_only",
        "claim_grade_label": "assumption_directional_support",
    }


def _attribution_rows(
    dose_mode: str,
    off_full: dict[str, str],
    on_full: dict[str, str],
    capex_drag_base: Decimal,
) -> list[dict[str, str]]:
    household_corporate_flow_n = _d(on_full["N_bil"]) - _d(off_full["N_bil"])
    rotation_side_d = _d(on_full["D_bil"]) - _d(off_full["D_bil"])
    rows = [
        {
            "row_type": "attribution",
            "dose_mode": dose_mode,
            "rule": "household_and_corporate_financial_claim_yield",
            "delta_N_bil": _fmt(household_corporate_flow_n),
            "delta_D_bil": "0",
            "delta_RW_component_note": "recomputed_in_on_vs_off_pair",
            "overlap_type": "allocation_financial_claim_yield",
            "overlap_key": f"allocation_financial_claim_yield|{dose_mode}|deposit_mmf_treasury_routes",
            "include_flag": "1",
            "include_in_reconciliation": "1",
            "input_basis_label": "scenario_only",
            "claim_grade_label": "assumption_directional_support",
        },
        {
            "row_type": "attribution",
            "dose_mode": dose_mode,
            "rule": "rotation_side_d_recomposition",
            "delta_N_bil": "0",
            "delta_D_bil": _fmt(rotation_side_d),
            "delta_RW_component_note": "deposit/MMF/treasury funding recomposition from allocation scenario rows",
            "overlap_type": "rotation_side_d_recomposition",
            "overlap_key": f"rotation_side_d_recomposition|{dose_mode}|deposit_mmf_treasury_routes",
            "include_flag": "1",
            "include_in_reconciliation": "1",
            "input_basis_label": "scenario_only",
            "claim_grade_label": "assumption_directional_support",
        },
        {
            "row_type": "excluded_overlap_with_6B_user_cost",
            "dose_mode": dose_mode,
            "rule": "corporate_capex_allocation_drag",
            "delta_N_bil": "0",
            "delta_D_bil": "0",
            "excluded_D_candidate_bil": _fmt(capex_drag_base),
            "delta_RW_component_note": "excluded: Gormsen-Huber passthrough measures the same user-cost investment response already carried by 6B",
            "overlap_type": "user_cost_vs_allocation_capex",
            "overlap_key": f"excluded_overlap_with_6B_user_cost|{dose_mode}|firm_sector|2026|base",
            "include_flag": "0",
            "include_in_reconciliation": "0",
            "input_basis_label": "scenario_only",
            "claim_grade_label": "assumption_directional_support",
        },
    ]
    rows.append(_reconciliation_residual_row(dose_mode, off_full, on_full, rows))
    return rows


def _reconciliation_residual_row(
    dose_mode: str,
    off_full: dict[str, str],
    on_full: dict[str, str],
    attribution_rows: list[dict[str, str]],
) -> dict[str, str]:
    total_n = _d(on_full["N_bil"]) - _d(off_full["N_bil"])
    total_d = _d(on_full["D_bil"]) - _d(off_full["D_bil"])
    attributed_n = sum(
        _d(row["delta_N_bil"])
        for row in attribution_rows
        if row.get("include_in_reconciliation") == "1"
    )
    attributed_d = sum(
        _d(row["delta_D_bil"])
        for row in attribution_rows
        if row.get("include_in_reconciliation") == "1"
    )
    return {
        "row_type": "interaction_residual",
        "dose_mode": dose_mode,
        "rule": "interaction_residual",
        "delta_N_bil": _fmt(total_n - attributed_n),
        "delta_D_bil": _fmt(total_d - attributed_d),
        "delta_RW_component_note": "explicit residual after per-rule rows; exact zero means rows reconcile to ON-vs-OFF totals",
        "overlap_type": "allocation_reconciliation_residual",
        "overlap_key": f"allocation_reconciliation_residual|{dose_mode}|2026|base",
        "include_flag": "1",
        "include_in_reconciliation": "1",
        "input_basis_label": "scenario_only",
        "claim_grade_label": "assumption_directional_support",
    }


def _financialization_interaction_rows(
    pack_dir: Path,
    output_root: Path,
) -> tuple[dict[str, str], dict[str, str]]:
    with tempfile.TemporaryDirectory(prefix="rwtas_f_asset_allocation_") as tmp:
        tmp_root = Path(tmp)
        off_pack = tmp_root / "F-asset-25_allocation_off"
        shutil.copytree(pack_dir, off_pack)
        scenario_rows, split_rows, claim_rules = _financialization_config_rows(pack_dir, "F-asset-25")
        _append_csv_rows(off_pack / "scenario_adjustments.csv", scenario_rows)
        _append_csv_rows(off_pack / "household_stock_splits.csv", split_rows)
        _append_csv_rows(off_pack / "claim_processor_rules.csv", claim_rules)
        off_result = build_v1(off_pack, dose_mode=DEFAULT_DOSE_MODE, shock_size_bp=Decimal("100"))
        off_paths = write_v1_outputs(
            off_result,
            output_root / "financialization_interaction" / "F-asset-25_allocation_off",
        )

        on_pack = tmp_root / "F-asset-25_allocation_on"
        shutil.copytree(off_pack, on_pack)
        allocation_rows, allocation_splits, allocation_rules, _ = _allocation_config_rows(
            off_pack,
            DEFAULT_DOSE_MODE,
        )
        _append_csv_rows(on_pack / "scenario_adjustments.csv", allocation_rows)
        _append_csv_rows(on_pack / "household_stock_splits.csv", allocation_splits)
        _append_csv_rows(on_pack / "claim_processor_rules.csv", allocation_rules)
        on_result = build_v1(on_pack, dose_mode=DEFAULT_DOSE_MODE, shock_size_bp=Decimal("100"))
        on_paths = write_v1_outputs(
            on_result,
            output_root / "financialization_interaction" / "F-asset-25_allocation_on",
        )

    off = _full_headline(_default_headline(off_result))
    on = _full_headline(_default_headline(on_result))
    return (
        off | {"row_type": "financialization_interaction_off"},
        {
            "row_type": "financialization_interaction",
            "scenario": "F-asset-25 + allocation",
            "base_financialization_scenario": "F-asset-25",
            "allocation_layer_scope": "full_rotation_plus_corporate_cash_leg_capex_excluded",
            "allocation_off_N_bil": off["N_bil"],
            "allocation_off_D_bil": off["D_bil"],
            "allocation_off_RW": off["RW_ratio"],
            "allocation_on_N_bil": on["N_bil"],
            "allocation_on_D_bil": on["D_bil"],
            "allocation_on_RW": on["RW_ratio"],
            "delta_N_bil": _fmt(_d(on["N_bil"]) - _d(off["N_bil"])),
            "delta_D_bil": _fmt(_d(on["D_bil"]) - _d(off["D_bil"])),
            "delta_RW": _fmt(_d(on["RW_ratio"]) - _d(off["RW_ratio"])),
            "source_rollup_path": str(off_paths["out_ratewall_rollup"]),
            "allocation_on_rollup_path": str(on_paths["out_ratewall_rollup"]),
            "input_basis_label": "scenario_only",
            "claim_grade_label": "assumption_directional_support",
        },
    )


def _full_headline(headline: dict[str, str]) -> dict[str, str]:
    return {
        "N_bil": headline["N_bil"],
        "D_bil": headline["D_bil"],
        "net_bil": headline["net_bil"],
        "RW_ratio": headline["RW_ratio"],
    }


def _default_headline(result: object) -> dict[str, str]:
    return [
        row
        for row in result.rows("out_ratewall_rollup")
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]


def _parameter_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for parameter_id, values in PARAMETER_BANDS.items():
        rows.append(
            {
                "row_type": "parameter",
                "parameter_id": parameter_id,
                "low": _fmt(values["low"]),
                "base": _fmt(values["base"]),
                "high": _fmt(values["high"]),
                "units": str(values["units"]),
                "grade": str(values["grade"]),
                "input_basis_label": "scenario_only",
                "claim_grade_label": "B" if parameter_id == "hurdle_passthrough" else "assumption_directional_support",
                "source": "do/rwtas_allocation_layer_evidence_20260703.md",
            }
        )
    rows.append(
        {
            "row_type": "excluded_with_evidence",
            "parameter_id": "buyback_equity_supply_leg",
            "low": "",
            "base": "",
            "high": "",
            "units": "not_wired",
            "grade": "D",
            "input_basis_label": "scenario_only",
            "claim_grade_label": "assumption_directional_support",
            "source": "do/rwtas_allocation_layer_evidence_20260703.md",
            "disposition": "excluded: memo found buybacks profit/cash-driven more than rate-driven over the relevant short run",
        }
    )
    return rows


def _flow_config_row(
    dose_mode: str,
    leg: str,
    amounts: dict[str, Decimal],
    routes: dict[str, dict[str, Decimal]],
) -> dict[str, str]:
    out = {
        "row_type": "flow_config",
        "dose_mode": dose_mode,
        "leg": leg,
        "amount_low_bil": _fmt(amounts["low"]),
        "amount_base_bil": _fmt(amounts["base"]),
        "amount_high_bil": _fmt(amounts["high"]),
        "hurdle_damping_context_base": _fmt(_param("hurdle_passthrough", "base")) if leg == "corporate" else "0",
        "input_basis_label": "scenario_only",
        "claim_grade_label": "assumption_directional_support",
        "overlap_type": "allocation_flow_config",
        "overlap_key": f"allocation_flow_config|{dose_mode}|{leg}|2026|base",
        "include_flag": "1",
    }
    for family, values in routes.items():
        out[f"route_{family}_base_bil"] = _fmt(values["base"])
    return out


def _lineage_rows() -> list[dict[str, str]]:
    return [
        {
            "deliverable_column": "allocation_spread",
            "source_file": "src/ratewall/rwtas/v1.py:_treasury_yield_delta_bp; owner risky-real baseline delta=0",
            "lineage_note": "safe leg uses experiment curve; risky/real baseline is a flagged owner-assumption no-delta comparator",
        },
        {
            "deliverable_column": "household_rotation_elasticity;stock_reallocation_share;hurdle_passthrough;corporate_financial_allocation_share",
            "source_file": "do/rwtas_allocation_layer_evidence_20260703.md",
            "lineage_note": "L/B/H and grades wired verbatim; values are scenario inputs, not fitted outputs",
        },
        {
            "deliverable_column": "rotation_reversal_share",
            "source_file": "src/ratewall/rwtas/hysteresis.py:REVERSAL_SHARE_BANDS",
            "lineage_note": "ratchet convention reused for outflow/down-spread asymmetry",
        },
        {
            "deliverable_column": "corporate_capex_allocation_drag",
            "source_file": "configs/rwtas/packs/phase6/conversion_parameters.csv:business_fixed_investment_baseline_annual",
            "lineage_note": "excluded_overlap_with_6B_user_cost; Gormsen-Huber passthrough measures the investment response already carried by 6B",
        },
    ]


def _overlap_probe_rows(
    flow_rows: list[dict[str, str]],
    attribution_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    actual = [
        {
            "probe_group": "actual_rows",
            "overlap_type": row["overlap_type"],
            "overlap_key": row["overlap_key"],
            "channel": row.get("leg") or row.get("rule", ""),
            "include_flag": row.get("include_flag", "1"),
            "source_row_type": row.get("row_type", ""),
        }
        for row in flow_rows + attribution_rows
        if row.get("overlap_type") and row.get("overlap_key")
    ]
    capex_row = [
        row
        for row in actual
        if row["overlap_type"] == "user_cost_vs_allocation_capex"
    ][0]
    flow_row = [
        row
        for row in actual
        if row["overlap_type"] == "allocation_flow_config" and row["channel"] == "household"
    ][0]
    duplicate_user_cost = actual + [
        dict(capex_row, channel="allocation_capex_injected", include_flag="1"),
        dict(capex_row, channel="6B_user_cost_injected", include_flag="1"),
    ]
    duplicate_flow = actual + [dict(flow_row, channel="corporate_financial_route_injected")]
    actual_errors = validate_allocation_overlap_rows(actual)
    user_cost_errors = validate_allocation_overlap_rows(duplicate_user_cost)
    flow_errors = validate_allocation_overlap_rows(duplicate_flow)
    return [
        _probe_row("actual_rows_distinct", not actual_errors, actual_errors),
        _probe_row("user_cost_double_count_injection_fails", bool(user_cost_errors), user_cost_errors),
        _probe_row("actual_flow_duplicate_injection_fails", bool(flow_errors), flow_errors),
    ]


def validate_allocation_overlap_rows(rows: list[dict[str, str]]) -> list[str]:
    active: set[tuple[str, str]] = set()
    errors: list[str] = []
    for row in rows:
        if row.get("include_flag") not in {"1", "true", "True"}:
            continue
        key = (row.get("overlap_type", ""), row.get("overlap_key", ""))
        if key in active:
            errors.append(f"duplicate allocation overlap key {key[0]}::{key[1]}")
        active.add(key)
    return errors


def _probe_row(check_id: str, passed: bool, errors: list[str]) -> dict[str, str]:
    return {
        "row_type": "overlap_probe",
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "message": ";".join(errors) if errors else "overlap rule behaved as expected",
        "input_basis_label": "scenario_only",
        "claim_grade_label": "assumption_directional_support",
    }


def _caveat_rows() -> list[dict[str, str]]:
    caveats = [
        "partial_equilibrium_bound_no_flow_to_price_feedback",
        "regime_valid_for_2022_2024_like_high_safe_yield_conditions",
        "D_grade_parameters_displayed_not_claim_grade",
    ]
    return [
        {
            "row_type": "caveat",
            "caveat_id": caveat,
            "input_basis_label": "scenario_only",
            "claim_grade_label": "assumption_directional_support",
        }
        for caveat in caveats
    ]


def _stamp_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    stamped: list[dict[str, str]] = []
    for row in rows:
        out = dict(row)
        out.setdefault("input_basis_label", "scenario_only")
        out.setdefault("claim_grade_label", "assumption_directional_support")
        stamped.append(out)
    return stamped


def _rectangular_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    return [{field: row.get(field, "") for field in fields} for row in rows]


def _captioned_tables(
    tables: dict[str, list[dict[str, str]]],
    caption_note: str,
) -> dict[str, list[dict[str, str]]]:
    return {
        name: [
            row if row.get("caption_note") else row | {"caption_note": caption_note}
            for row in rows
        ]
        for name, rows in tables.items()
    }


def _param(parameter_id: str, band: str) -> Decimal:
    return PARAMETER_BANDS[parameter_id][band]  # type: ignore[return-value]


def _phase6_param(pack: dict[str, list[dict[str, str]]], parameter_id: str, band: str) -> Decimal:
    for row in pack["conversion_parameters"]:
        if row["parameter_id"] == parameter_id:
            return _d(row[band])
    raise ValueError(f"missing phase6 parameter {parameter_id}")


def _holder_from_cell(cell_or_sector: str) -> str:
    for part in cell_or_sector.split("|"):
        if part.startswith("holder="):
            return part.split("=", 1)[1]
    return cell_or_sector


def _markdown_table(title: str, rows: list[dict[str, str]], max_rows: int = 12) -> list[str]:
    if not rows:
        return ["", f"## {title}", "", "_No rows._"]
    fields = list(rows[0])
    if len(fields) > 8:
        preferred = [
            field
            for field in [
                "dose_mode",
                "scenario",
                "rule",
                "band",
                "allocation_off_N_bil",
                "allocation_on_N_bil",
                "delta_N_bil",
                "delta_D_bil",
                "delta_RW",
                "status",
                "message",
                "source_file",
            ]
            if field in rows[0]
        ]
        fields = preferred or fields[:8]
    lines = ["", f"## {title}", "", "| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    for row in rows[:max_rows]:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    if len(rows) > max_rows:
        lines.append(f"\n_{len(rows) - max_rows} more rows in CSV._")
    return lines
