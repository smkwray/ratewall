"""Writer-support RWTAM scenario readouts.

These outputs are scenario/readout-only.  They reuse the V1 monthly machinery
with in-memory pack mutations and do not rewrite the default V1 headline.
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from ratewall.rwtam.v1 import (
    DEFAULT_DOSE_MODE,
    _annual_records_from_monthly,
    _d,
    _effective_pack,
    _fmt,
    _load_pack,
    _monthly_records,
    _output_tables,
    _read_csv_rows,
    _write_rows,
    build_v1,
    validate_pack,
)


PACK_DIR = Path("configs/rwtam/packs")
OUTPUT_DIR = Path("var/rwtam/scenarios/writer_rider")
REPORT_PATH = Path("do/rwtam_writer_rider_report_20260705.md")
CONVERSION_SOURCE = Path("configs/rwtam/packs/conversion_coefficients.csv")
TERM_PREMIUM_SOURCE = (
    "configs/rwtam/packs/term_premium_response/"
    "rwtam_term_premium_response_bands_2026-07-02/parameters_term_premium.csv"
)

CONVERTING_CELLS = (
    "hh_constrained_net_borrower",
    "hh_middle_owner_illiquid",
    "hh_retiree_fixed_income_saver",
    "hh_unconstrained_saver",
    "firm_bank_dependent_small",
    "firm_market_funded_large",
    "state_local_public_cell",
)
SUMMARY_PERIODS = (
    ("annual", "2026"),
    ("cumulative_120_month", "2026-2035"),
)


def build_writer_rider_outputs(
    pack_dir: Path = PACK_DIR,
    output_dir: Path = OUTPUT_DIR,
    report_path: Path = REPORT_PATH,
) -> dict[str, Path]:
    """Build and write the two writer-rider readout CSVs and report."""

    output_dir.mkdir(parents=True, exist_ok=True)
    conversion_rows = build_conversion_tornado_rows(pack_dir)
    parallel_rows = build_parallel_curve_comparator_rows(pack_dir)
    paths = {
        "out_conversion_tornado": output_dir / "out_conversion_tornado.csv",
        "out_parallel_curve_comparator": output_dir
        / "out_parallel_curve_comparator.csv",
    }
    _write_rows(paths["out_conversion_tornado"], conversion_rows)
    _write_rows(paths["out_parallel_curve_comparator"], parallel_rows)
    write_writer_rider_report(report_path, conversion_rows, parallel_rows)
    paths["report"] = report_path
    return paths


def build_conversion_tornado_rows(
    pack_dir: Path = PACK_DIR,
) -> list[dict[str, str]]:
    base_tables = build_v1(pack_dir, include_impulse_beta_comparator=False).tables
    base_by_period = _headline_by_period(base_tables)
    coefficient_rows = _conversion_coefficient_rows(pack_dir)
    rows: list[dict[str, str]] = []

    for period_type, period in SUMMARY_PERIODS:
        base = base_by_period[(period_type, period)]
        rows.append(
            _conversion_row(
                run_id="base_default",
                run_type="base",
                cell_or_sector="all_base_coefficients",
                parameter_id="",
                coefficient_variant="base",
                coefficient_value="",
                period_type=period_type,
                period=period,
                run=base,
                base=base,
                note="Default headline run; included only as the frozen comparison anchor.",
            )
        )

    run_tables: dict[str, dict[str, list[dict[str, str]]]] = {}
    for coefficient in coefficient_rows:
        cell = coefficient["cell_or_sector"]
        for variant in ("low", "high"):
            run_id = f"{cell}__{variant}"
            run_tables[run_id] = _run_v1_tables_from_pack(
                pack_dir,
                conversion_overrides={cell: coefficient[variant]},
            )
            for period_type, period in SUMMARY_PERIODS:
                rows.append(
                    _conversion_row(
                        run_id=run_id,
                        run_type="single_cell",
                        cell_or_sector=cell,
                        parameter_id=coefficient["parameter_id"],
                        coefficient_variant=variant,
                        coefficient_value=coefficient[variant],
                        period_type=period_type,
                        period=period,
                        run=_headline_by_period(run_tables[run_id])[(period_type, period)],
                        base=base_by_period[(period_type, period)],
                        note="scenario_only;sensitivity_readout",
                    )
                )

    for variant in ("low", "high"):
        run_id = f"all_conversion_coefficients__{variant}"
        run_tables[run_id] = _run_v1_tables_from_pack(
            pack_dir,
            conversion_overrides={
                coefficient["cell_or_sector"]: coefficient[variant]
                for coefficient in coefficient_rows
            },
        )
        for period_type, period in SUMMARY_PERIODS:
            rows.append(
                _conversion_row(
                    run_id=run_id,
                    run_type="conversion_only_envelope",
                    cell_or_sector="all_converting_cells",
                    parameter_id="all_conversion_coefficients",
                    coefficient_variant=variant,
                    coefficient_value="",
                    period_type=period_type,
                    period=period,
                    run=_headline_by_period(run_tables[run_id])[(period_type, period)],
                    base=base_by_period[(period_type, period)],
                    note=(
                        "scenario_only;sensitivity_readout;conversion-only envelope: "
                        "only conversion coefficients move, distinct from the global "
                        "band envelope that moves every banded parameter jointly"
                    ),
                )
            )
    rows.extend(_conversion_notes_rows(rows))
    return rows


def build_parallel_curve_comparator_rows(
    pack_dir: Path = PACK_DIR,
) -> list[dict[str, str]]:
    headline = build_v1(pack_dir, include_impulse_beta_comparator=False).tables
    tp_off = _run_v1_tables_from_pack(pack_dir, term_premium_zero=True)
    rows: list[dict[str, str]] = []
    headline_by_period = _headline_by_period(headline)
    tp_off_by_period = _headline_by_period(tp_off)

    for period_type, period in SUMMARY_PERIODS:
        headline_row = headline_by_period[(period_type, period)]
        tp_off_row = tp_off_by_period[(period_type, period)]
        rows.append(
            _parallel_summary_row(
                scenario_id="headline_tp_on",
                period_type=period_type,
                period=period,
                row=headline_row,
                peer=headline_row,
                basis=(
                    "headline curve: expectations-consistent + estimated term-premium response"
                ),
            )
        )
        rows.append(
            _parallel_summary_row(
                scenario_id="parallel_tp_off",
                period_type=period_type,
                period=period,
                row=tp_off_row,
                peer=headline_row,
                basis=(
                    "comparator_only: persistent expectations leg +100bp flat; "
                    "all term-premium deltas forced to zero"
                ),
            )
        )
        rows.extend(_parallel_family_gap_rows(headline, tp_off, period_type, period))
    rows.extend(_parallel_bill_invariant_rows(headline, tp_off))

    rows.append(
        {
            "row_type": "note",
            "scenario_id": "parallel_curve_comparator_note",
            "period_type": "",
            "period": "",
            "instrument_family": "",
            "N_bil": "",
            "D_bil": "",
            "RW_ratio": "",
            "headline_N_bil": "",
            "headline_D_bil": "",
            "headline_RW_ratio": "",
            "tp_off_N_bil": "",
            "tp_off_D_bil": "",
            "tp_off_RW_ratio": "",
            "gap_N_bil": "",
            "gap_D_bil": "",
            "gap_RW": "",
            "lineage": TERM_PREMIUM_SOURCE,
            "basis": (
                "Headline curve is expectations-consistent plus estimated TP response; "
                "parallel cell is the familiar-benchmark comparator. Current V1 "
                "Treasury coupon repricing uses the 10y representative coupon rate; "
                "30y TP parameters are zeroed in this comparator but have no separate "
                "active family leg in the present run."
            ),
            "label": "comparator_only",
        }
    )
    return rows


def write_writer_rider_report(
    output_path: Path,
    conversion_rows: list[dict[str, str]],
    parallel_rows: list[dict[str, str]],
    *,
    validation_line: str = "Pytest gate counts: NOT RUN IN BUILD SCRIPT",
) -> Path:
    conversion_data = [row for row in conversion_rows if row["row_type"] == "run"]
    single_year = [
        row
        for row in conversion_data
        if row["run_type"] == "single_cell" and row["period_type"] == "annual"
    ]
    largest_n = sorted(
        single_year,
        key=lambda row: abs(_d(row["delta_N_vs_base_bil"])),
        reverse=True,
    )[:3]
    largest_d = sorted(
        single_year,
        key=lambda row: abs(_d(row["delta_D_vs_base_bil"])),
        reverse=True,
    )[:3]
    tp_family = [
        row
        for row in parallel_rows
        if row["row_type"] == "family_gap"
        and row["period_type"] == "annual"
        and (row["gap_N_bil"] != "0" or row["gap_D_bil"] != "0")
    ]
    lines = [
        "# RWTAM writer-support rider report",
        "",
        "Date: 2026-07-05.",
        "Scope: scenario/readout-only conversion-coefficient tornado and parallel-curve comparator.",
        "",
        "## Deliverables",
        "",
        f"- `out_conversion_tornado.csv`: {len(conversion_data)} run-period rows plus notes.",
        f"- `out_parallel_curve_comparator.csv`: {len(parallel_rows)} rows including TP-on/TP-off summaries, direct family gaps, and note row.",
        "",
        "## Conversion Tornado",
        "",
        "- Disposition: built one-at-a-time low/high coefficient runs for the four household cells, two firm cells, and state/local public cell; skipped the all-firms fallback and flagged payer-loss asymmetry sensitivity.",
        "- Lineage: `configs/rwtam/packs/conversion_coefficients.csv`; all mutations are in-memory and set only the target coefficient to its L/H value while other parameters stay at base for reported rows.",
        "- Envelope: emitted all-low/all-high conversion-only rows; this is not the global band envelope because no other banded parameter is moved.",
        "- Dominance rule: `N` if absolute delta-N exceeds absolute delta-D, `D` if the reverse, `tie` only at exact equality.",
        "",
        "| largest year-1 N movers | variant | dN | dD | dRW | dominant |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in largest_n:
        lines.append(
            f"| {row['cell_or_sector']} | {row['coefficient_variant']} | "
            f"{row['delta_N_vs_base_bil']} | {row['delta_D_vs_base_bil']} | "
            f"{row['delta_RW_vs_base']} | {row['dominant_side']} |"
        )
    lines.extend(
        [
            "",
            "| largest year-1 D movers | variant | dN | dD | dRW | dominant |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in largest_d:
        lines.append(
            f"| {row['cell_or_sector']} | {row['coefficient_variant']} | "
            f"{row['delta_N_vs_base_bil']} | {row['delta_D_vs_base_bil']} | "
            f"{row['delta_RW_vs_base']} | {row['dominant_side']} |"
        )
    lines.extend(
        [
            "",
            "## Parallel-Curve Comparator",
            "",
            "- Disposition: built TP-off as base-band persistent +100bp expectations path with all term-premium parameters zeroed at all tenors.",
            "- Lineage: default `build_v1` headline versus in-memory zeroed `term_premium_parameters` run; gaps are direct TP-off minus headline comparisons, not complement residuals.",
            "- Notes: bills carry no TP; the first-month bill-side N leg is byte-identical before endogenous public-net debt feedback changes later bill stocks. Annual/cumulative bill-family rows are left as direct paired-run results. Current V1 coupon repricing uses the 10y representative coupon rate, so the +15bp 10y TP removal drives active coupon-family movement; the +20bp 30y TP parameter is zeroed but has no separate active family leg in this run.",
            "",
            "| year-1 moving family | gap N | gap D | basis |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for row in tp_family:
        lines.append(
            f"| {row['instrument_family']} | {row['gap_N_bil']} | "
            f"{row['gap_D_bil']} | {row['basis']} |"
        )
    lines.extend(
        [
            "",
            "## Validation",
            "",
            f"- {validation_line}",
            "- Headline/golden files: no code path writes V1 default output or fixtures; scenario outputs are confined to `var/rwtam/scenarios/writer_rider/`.",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _run_v1_tables_from_pack(
    pack_dir: Path,
    *,
    conversion_overrides: dict[str, str] | None = None,
    term_premium_zero: bool = False,
) -> dict[str, list[dict[str, str]]]:
    raw_pack = deepcopy(_load_pack(pack_dir))
    if conversion_overrides:
        for row in raw_pack["conversion_coefficients"]:
            override = conversion_overrides.get(row["cell_or_sector"])
            if override is None:
                continue
            row["low"] = override
            row["base"] = override
            row["high"] = override
    if term_premium_zero:
        for row in raw_pack["term_premium_parameters"]:
            if row["parameter_id"].startswith("delta_tp_"):
                row["low"] = "0"
                row["base"] = "0"
                row["high"] = "0"
    pack = _effective_pack(raw_pack, True, True)
    phase6_pack = _load_pack(pack_dir / "phase6")
    validation = validate_pack(pack, phase6_pack)
    monthly_records = _monthly_records(
        pack,
        include_tdc_settlement=True,
        shock_start_month="2026-01",
        dose_mode=DEFAULT_DOSE_MODE,
        include_tax_layer=True,
    )
    records = _annual_records_from_monthly(monthly_records)
    return _output_tables(
        pack,
        phase6_pack,
        records,
        validation,
        pack_dir,
        monthly_records=monthly_records,
        dose_mode=DEFAULT_DOSE_MODE,
        include_tax_layer=True,
    )


def _conversion_coefficient_rows(pack_dir: Path) -> list[dict[str, str]]:
    rows = _read_csv_rows(pack_dir / "conversion_coefficients.csv")
    return [
        row
        for row in rows
        if row["cell_or_sector"] in CONVERTING_CELLS and _d(row["base"]) != 0
    ]


def _headline_by_period(
    tables: dict[str, list[dict[str, str]]],
) -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in tables["out_ratewall_rollup"]:
        if row["band"] != "base" or row["ricardian_offset"] != "0":
            continue
        key = (row["period_type"], row["period"])
        if key in SUMMARY_PERIODS:
            out[key] = row
    return out


def _family_by_period(
    tables: dict[str, list[dict[str, str]]],
    period_type: str,
    period: str,
) -> dict[str, dict[str, str]]:
    return {
        row["instrument_family"]: row
        for row in tables["out_cashflow_family_contributions"]
        if row["period_type"] == period_type
        and row["period"] == period
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    }


def _conversion_row(
    *,
    run_id: str,
    run_type: str,
    cell_or_sector: str,
    parameter_id: str,
    coefficient_variant: str,
    coefficient_value: str,
    period_type: str,
    period: str,
    run: dict[str, str],
    base: dict[str, str],
    note: str,
) -> dict[str, str]:
    delta_n = _d(run["N_bil"]) - _d(base["N_bil"])
    delta_d = _d(run["D_bil"]) - _d(base["D_bil"])
    delta_rw = _d(run["RW_ratio"]) - _d(base["RW_ratio"])
    dominant = "tie"
    if abs(delta_n) > abs(delta_d):
        dominant = "N"
    elif abs(delta_d) > abs(delta_n):
        dominant = "D"
    return {
        "row_type": "run",
        "run_id": run_id,
        "run_type": run_type,
        "cell_or_sector": cell_or_sector,
        "parameter_id": parameter_id,
        "coefficient_variant": coefficient_variant,
        "coefficient_value": coefficient_value,
        "period_type": period_type,
        "period": period,
        "dose_mode": run["dose_mode"],
        "scenario_role": "scenario_only;sensitivity_readout",
        "N_bil": run["N_bil"],
        "D_bil": run["D_bil"],
        "RW_ratio": run["RW_ratio"],
        "base_N_bil": base["N_bil"],
        "base_D_bil": base["D_bil"],
        "base_RW_ratio": base["RW_ratio"],
        "delta_N_vs_base_bil": _fmt(delta_n),
        "delta_D_vs_base_bil": _fmt(delta_d),
        "delta_RW_vs_base": _fmt(delta_rw),
        "dominant_side": dominant,
        "dominance_basis": "abs(delta_N_vs_base_bil) vs abs(delta_D_vs_base_bil)",
        "lineage": str(CONVERSION_SOURCE),
        "note": note,
    }


def _conversion_notes_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    template = {field: "" for field in rows[0]}
    return [
        template
        | {
            "row_type": "note",
            "run_id": "conversion_only_envelope_note",
            "scenario_role": "scenario_only;sensitivity_readout",
            "lineage": str(CONVERSION_SOURCE),
            "note": (
                "Envelope rows set all converting coefficients to L or H. "
                "They intentionally do not move other banded pack parameters, "
                "so they are distinct from the global low/high band envelope."
            ),
        }
    ]


def _parallel_summary_row(
    *,
    scenario_id: str,
    period_type: str,
    period: str,
    row: dict[str, str],
    peer: dict[str, str],
    basis: str,
) -> dict[str, str]:
    return {
        "row_type": "summary",
        "scenario_id": scenario_id,
        "period_type": period_type,
        "period": period,
        "instrument_family": "",
        "N_bil": row["N_bil"],
        "D_bil": row["D_bil"],
        "RW_ratio": row["RW_ratio"],
        "headline_N_bil": peer["N_bil"],
        "headline_D_bil": peer["D_bil"],
        "headline_RW_ratio": peer["RW_ratio"],
        "tp_off_N_bil": row["N_bil"] if scenario_id == "parallel_tp_off" else "",
        "tp_off_D_bil": row["D_bil"] if scenario_id == "parallel_tp_off" else "",
        "tp_off_RW_ratio": row["RW_ratio"] if scenario_id == "parallel_tp_off" else "",
        "gap_N_bil": _fmt(_d(row["N_bil"]) - _d(peer["N_bil"])),
        "gap_D_bil": _fmt(_d(row["D_bil"]) - _d(peer["D_bil"])),
        "gap_RW": _fmt(_d(row["RW_ratio"]) - _d(peer["RW_ratio"])),
        "lineage": TERM_PREMIUM_SOURCE,
        "basis": basis,
        "label": "comparator_only" if scenario_id == "parallel_tp_off" else "headline",
    }


def _parallel_family_gap_rows(
    headline: dict[str, list[dict[str, str]]],
    tp_off: dict[str, list[dict[str, str]]],
    period_type: str,
    period: str,
) -> list[dict[str, str]]:
    headline_families = _family_by_period(headline, period_type, period)
    tp_off_families = _family_by_period(tp_off, period_type, period)
    rows: list[dict[str, str]] = []
    for family in sorted(set(headline_families) | set(tp_off_families)):
        h = headline_families.get(family)
        t = tp_off_families.get(family)
        h_n = _d(h["N_bil"]) if h else Decimal("0")
        h_d = _d(h["D_bil"]) if h else Decimal("0")
        t_n = _d(t["N_bil"]) if t else Decimal("0")
        t_d = _d(t["D_bil"]) if t else Decimal("0")
        if t_n == h_n and t_d == h_d and family != "treasury_bills":
            continue
        rows.append(
            {
                "row_type": "family_gap",
                "scenario_id": "parallel_tp_off_minus_headline",
                "period_type": period_type,
                "period": period,
                "instrument_family": family,
                "N_bil": "",
                "D_bil": "",
                "RW_ratio": "",
                "headline_N_bil": _fmt(h_n),
                "headline_D_bil": _fmt(h_d),
                "headline_RW_ratio": "",
                "tp_off_N_bil": _fmt(t_n),
                "tp_off_D_bil": _fmt(t_d),
                "tp_off_RW_ratio": "",
                "gap_N_bil": _fmt(t_n - h_n),
                "gap_D_bil": _fmt(t_d - h_d),
                "gap_RW": "",
                "lineage": (
                    "out_cashflow_family_contributions direct TP-off minus headline"
                ),
                "basis": _family_gap_basis(family),
                "label": "comparator_only;direct_family_gap",
            }
        )
    return rows


def _parallel_bill_invariant_rows(
    headline: dict[str, list[dict[str, str]]],
    tp_off: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    headline_bill = _monthly_family_row(headline, "2026-01", "treasury_bills")
    tp_off_bill = _monthly_family_row(tp_off, "2026-01", "treasury_bills")
    return [
        {
            "row_type": "bill_tp_invariant",
            "scenario_id": "parallel_tp_off_bill_side_assertion",
            "period_type": "monthly",
            "period": "2026-01",
            "instrument_family": "treasury_bills",
            "N_bil": "",
            "D_bil": "",
            "RW_ratio": "",
            "headline_N_bil": headline_bill["N_bil"],
            "headline_D_bil": headline_bill["D_bil"],
            "headline_RW_ratio": "",
            "tp_off_N_bil": tp_off_bill["N_bil"],
            "tp_off_D_bil": tp_off_bill["D_bil"],
            "tp_off_RW_ratio": "",
            "gap_N_bil": _fmt(_d(tp_off_bill["N_bil"]) - _d(headline_bill["N_bil"])),
            "gap_D_bil": _fmt(_d(tp_off_bill["D_bil"]) - _d(headline_bill["D_bil"])),
            "gap_RW": "",
            "lineage": "out_cashflow_family_contributions_monthly direct paired rows",
            "basis": (
                "first-month bill-side N/D byte-match asserted; later annual "
                "bill-family gaps are endogenous stock-feedback effects, not TP yield"
            ),
            "label": "comparator_only;bill_side_tp_invariant",
        }
    ]


def _monthly_family_row(
    tables: dict[str, list[dict[str, str]]],
    period: str,
    family: str,
) -> dict[str, str]:
    return [
        row
        for row in tables["out_cashflow_family_contributions_monthly"]
        if row["period_type"] == "monthly"
        and row["period"] == period
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
        and row["instrument_family"] == family
    ][0]


def _family_gap_basis(family: str) -> str:
    if family == "treasury_bills":
        return "direct paired-run annual/cumulative bill gap from endogenous stock feedback; bills carry no TP yield"
    if family == "treasury_coupon_current_stock_roll":
        return "coupon interest on current-stock roll; 10y TP removed from repriced coupon cohort"
    if family == "treasury_coupon_new_deficit_issuance":
        return "coupon interest on new issuance; 10y TP removed from new coupon cohort"
    if family == "tdc_created_deposit_income_from_deficit_financing":
        return "term-premium-linked D/N leg via lower government-interest-driven TDC stock"
    return "direct family comparison from paired runs"
