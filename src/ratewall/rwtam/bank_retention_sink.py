"""Promoted bank-retention deposit sink for RWTAM."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path

from ratewall.rwtam.credit_deposit_coupling import _credit_deposit_delta
from ratewall.rwtam.v1 import (
    BANDS,
    CURRENT_DEFAULT_OBJECT_STAMP,
    DEFAULT_DOSE_MODE,
    _d,
    _fmt,
    _load_pack,
    _read_csv_rows,
    _write_rows,
    build_v1,
)


EXPERIMENT_ID = "rwtam_bank_retention_sink_20260704"
OUTPUT_DIR = Path("var/rwtam/scenarios/bank_retention_sink")
REPORT_PATH = Path("do/rwtam_bank_retention_report_20260704.md")
LABEL = (
    "default_baseline;combined_sinks;bank_retention_sink;"
    "assumption_directional_support;banded_recycle_share"
)
PAYOUT_RECYCLE_SHARE_BANDS = {
    "low": Decimal("0.45"),
    "base": Decimal("0.60"),
    "high": Decimal("0.75"),
}
DEPOSIT_FAMILIES = (
    "deposits_checkable",
    "deposits_savings_mmda",
    "deposits_time_cds",
)
MIGRATION_BASE_FAMILIES = ("deposits_checkable",)
COMPETITION_BETA_STOCK_FAMILIES = ("deposits_savings_mmda", "deposits_time_cds")
BANK_EARNING_ASSET_RECEIPTS = {
    "iorb_receipts",
    "c_and_i_receipts",
    "a2_mortgage_whole_loan_receipts",
    "household_nonmortgage_floating_receipts",
    "household_consumer_new_flow_receipts",
    "treasury_security_receipts",
}
LOAN_RECEIPTS_ONLY = {
    "c_and_i_receipts",
    "a2_mortgage_whole_loan_receipts",
    "household_nonmortgage_floating_receipts",
    "household_consumer_new_flow_receipts",
}
HORIZONS = (
    ("year1_2026", "annual", "2026", "transient_12m"),
    ("year1_2026", "annual", "2026", "persistent_level"),
    ("persistent_120m", "cumulative_120_month", "2026-2035", "persistent_level"),
)


@dataclass(frozen=True)
class BankRetentionResult:
    """CSV-ready bank-retention sink output tables."""

    tables: dict[str, list[dict[str, str]]]

    def rows(self, table_name: str) -> list[dict[str, str]]:
        return self.tables[table_name]


def build_bank_retention_sink_experiment(
    pack_dir: Path = Path("configs/rwtam/packs"),
    *,
    output_root: Path = OUTPUT_DIR,
    shock_size_bp: Decimal = Decimal("100"),
) -> BankRetentionResult:
    """Build OFF, sink ON, family ablations, and combined-sink rows."""

    with localcontext() as context:
        context.prec = 28
        output_root.mkdir(parents=True, exist_ok=True)
        _clear_output_subdirs(output_root)
        base_pack = _load_pack(pack_dir)
        phase6_pack = _load_pack(pack_dir / "phase6")
        off_pack = export_bank_retention_off_pack(pack_dir, output_root / "packs" / "sink_off")
        off_builds = {
            dose_mode: build_v1(
                off_pack,
                dose_mode=dose_mode,
                shock_size_bp=shock_size_bp,
                include_impulse_beta_comparator=False,
            )
            for dose_mode in sorted({horizon[3] for horizon in HORIZONS})
        }
        credit_deltas = {
            band: _credit_deposit_delta(base_pack, phase6_pack, band, shock_size_bp)
            for band in BANDS
        }
        builds: dict[tuple[str, str, str], object] = {}
        sink_deltas: dict[tuple[str, str], dict[str, Decimal]] = {}
        nii_rows: list[dict[str, str]] = []
        for horizon_id, period_type, period, dose_mode in HORIZONS:
            horizon_key = _horizon_key(horizon_id, dose_mode)
            sink_deltas[(horizon_id, dose_mode)] = {}
            for band in BANDS:
                components = _nii_components(off_builds[dose_mode], band, horizon_id)
                retained = components["earning_asset_nii_delta_bil"] * (
                    Decimal("1") - PAYOUT_RECYCLE_SHARE_BANDS[band]
                )
                sink_deltas[(horizon_id, dose_mode)][band] = -retained
                nii_rows.append(
                    {
                        "experiment_id": EXPERIMENT_ID,
                        "horizon_id": horizon_id,
                        "period_type": period_type,
                        "period": period,
                        "dose_mode": dose_mode,
                        "band": band,
                        "earning_asset_receipts_bil": _fmt(components["earning_asset_receipts_bil"]),
                        "loan_receipts_only_bil": _fmt(components["loan_receipts_only_bil"]),
                        "deposit_interest_paid_bil": _fmt(components["deposit_interest_paid_bil"]),
                        "loan_receipts_only_minus_deposit_interest_bil": _fmt(
                            components["loan_receipts_only_bil"]
                            - components["deposit_interest_paid_bil"]
                        ),
                        "earning_asset_nii_delta_bil": _fmt(components["earning_asset_nii_delta_bil"]),
                        "bank_payout_recycle_share": _fmt(PAYOUT_RECYCLE_SHARE_BANDS[band]),
                        "retained_share": _fmt(Decimal("1") - PAYOUT_RECYCLE_SHARE_BANDS[band]),
                        "retained_nii_deposit_sink_bil": _fmt(retained),
                        "deposit_stock_delta_bil": _fmt(-retained),
                        "disposition": "used_depository_earning_asset_receipts_minus_deposit_interest;loan_only_diagnostic_reported",
                    }
                )
            delta_by_band = sink_deltas[(horizon_id, dose_mode)]
            for variant, families in (
                ("full", DEPOSIT_FAMILIES),
                ("migration_base", MIGRATION_BASE_FAMILIES),
                ("competition_beta_stock", COMPETITION_BETA_STOCK_FAMILIES),
            ):
                pack = export_bank_retention_pack(
                    pack_dir,
                    output_root / "packs" / f"{horizon_key}_{variant}",
                    delta_by_band,
                    families,
                )
                builds[(horizon_key, variant, dose_mode)] = build_v1(
                    pack,
                    dose_mode=dose_mode,
                    shock_size_bp=shock_size_bp,
                    include_impulse_beta_comparator=False,
                )
            credit_pack = export_bank_retention_pack(
                pack_dir,
                output_root / "packs" / f"{horizon_key}_credit_deposit_only",
                credit_deltas,
                DEPOSIT_FAMILIES,
            )
            both_pack = export_bank_retention_pack(
                pack_dir,
                output_root / "packs" / f"{horizon_key}_combined_sinks",
                {
                    band: credit_deltas[band] + delta_by_band[band]
                    for band in BANDS
                },
                DEPOSIT_FAMILIES,
            )
            builds[(horizon_key, "credit_deposit_only", dose_mode)] = build_v1(
                credit_pack,
                dose_mode=dose_mode,
                shock_size_bp=shock_size_bp,
                include_impulse_beta_comparator=False,
            )
            builds[(horizon_key, "combined_sinks", dose_mode)] = build_v1(
                both_pack,
                dose_mode=dose_mode,
                shock_size_bp=shock_size_bp,
                include_impulse_beta_comparator=False,
            )

        _write_measurement_rollups(output_root, off_builds, builds)
        rows = _experiment_rows(off_builds, builds, sink_deltas, credit_deltas, output_root)
        tables = {
            "out_bank_retention_sink": rows,
            "out_bank_retention_nii_construction": nii_rows,
            "out_bank_retention_invariant_check": _invariant_rows(pack_dir, off_builds, rows),
            "out_bank_retention_lineage": _lineage_rows(output_root),
            "out_bank_retention_caveats": _caveat_rows(),
        }
        return BankRetentionResult(tables=tables)


def export_bank_retention_pack(
    pack_dir: Path,
    out_dir: Path,
    deposit_delta_by_band: dict[str, Decimal],
    families: tuple[str, ...] = DEPOSIT_FAMILIES,
) -> Path:
    """Write a scenario pack with bank-issued deposits moved by band."""

    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(pack_dir, out_dir)
    rows = _read_csv_rows(out_dir / "opening_stocks.csv")
    for band, delta in deposit_delta_by_band.items():
        _apply_bank_deposit_delta(rows, band, delta, families)
    _write_rows(out_dir / "opening_stocks.csv", rows)
    return out_dir


def export_bank_retention_off_pack(pack_dir: Path, out_dir: Path) -> Path:
    """Write the explicit OFF scenario pack without mutating inputs."""

    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(pack_dir, out_dir)
    return out_dir


def write_bank_retention_outputs(
    result: BankRetentionResult,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, rows)
        paths[table_name] = path
    return paths


def write_bank_retention_report(
    result: BankRetentionResult,
    output_path: Path = REPORT_PATH,
) -> Path:
    rows = result.rows("out_bank_retention_sink")
    base = next(
        row
        for row in rows
        if row["row_type"] == "bank_retention_sink"
        and row["band"] == "base"
        and row["dose_mode"] == DEFAULT_DOSE_MODE
        and row["horizon_id"] == "year1_2026"
    )
    finding = (
        "bank retained NII is a deposit sink and lowers measured RW in the base persistent year-1 run"
        if _d(base["delta_RW"]) < 0
        else "base persistent year-1 bank-retention sink did not lower measured RW"
    )
    lines = [
        "# RWTAM bank-retention deposit sink",
        "",
        "Date: 2026-07-04.",
        f"Object stamp: `{CURRENT_DEFAULT_OBJECT_STAMP}`.",
        f"Frame: `{LABEL}`; mechanism default OFF; no headline/golden promotion.",
        "",
        "## Dispositions",
        "",
        "| item | disposition |",
        "| --- | --- |",
        "| bank_retention_sink | built as scenario-only exported-pack mechanism; default `build_v1` path byte-asserted |",
        "| NII construction | used existing `out_bank_receipt_pay_ledger`: depository-bank earning-asset receipts minus deposit interest paid; loan-only minus deposit-interest diagnostic is reported and not used because it has the wrong sign for retained bank NII in this ledger boundary |",
        "| recycle share | owner-flagged L/B/H `0.45/0.60/0.75`; lineage: FDIC QBP / large-bank payout ratios plus expense-share rationale; `assumption_directional_support` only |",
        "| retained share | `(1 - bank_payout_recycle_share)` destroys M1/M2-perimeter bank deposits in the shocked run |",
        "| ablations | independent exported-pack runs: all deposit families, checkable-only, savings/CD-only; residual is full minus the two family-subset runs |",
        "| combined sinks | credit-deposit coupling and bank-retention sink measured as separate independent runs plus a both-ON run; interaction computed from runs |",
        "| QT rider | V1 `qt_supply_stress` now carries scenario-only deposit destruction equal to QT runoff times nonbank absorption share; default remains zero |",
        "| perimeter note | `m2_perimeter_note` caveat emitted; cross-border payments can move deposits out of perimeter without system-wide destruction and FX remains in the FX demand layer |",
        "",
        f"Finding statement: **{finding}.**",
    ]
    lines.extend(_markdown_table("Delta RW Table", rows))
    lines.extend(_markdown_table("NII Construction", result.rows("out_bank_retention_nii_construction")))
    lines.extend(_markdown_table("Invariants", result.rows("out_bank_retention_invariant_check")))
    lines.extend(_markdown_table("Lineage", result.rows("out_bank_retention_lineage")))
    lines.extend(_markdown_table("Caveats", result.rows("out_bank_retention_caveats")))
    lines.extend(
        [
            "",
            "## Output Locations",
            "",
            "- `var/rwtam/scenarios/bank_retention_sink/out_bank_retention_sink.csv`",
            "- `var/rwtam/scenarios/bank_retention_sink/out_bank_retention_nii_construction.csv`",
            "- `var/rwtam/scenarios/bank_retention_sink/out_bank_retention_invariant_check.csv`",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _experiment_rows(
    off_builds: dict[str, object],
    builds: dict[tuple[str, str, str], object],
    sink_deltas: dict[tuple[str, str], dict[str, Decimal]],
    credit_deltas: dict[str, Decimal],
    output_root: Path,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for horizon_id, period_type, period, dose_mode in HORIZONS:
        horizon_key = _horizon_key(horizon_id, dose_mode)
        for band in BANDS:
            off = _headline(off_builds[dose_mode], period_type, period, band)
            full = _headline(builds[(horizon_key, "full", dose_mode)], period_type, period, band)
            checkable = _headline(builds[(horizon_key, "migration_base", dose_mode)], period_type, period, band)
            savings_cd = _headline(builds[(horizon_key, "competition_beta_stock", dose_mode)], period_type, period, band)
            credit = _headline(builds[(horizon_key, "credit_deposit_only", dose_mode)], period_type, period, band)
            both = _headline(builds[(horizon_key, "combined_sinks", dose_mode)], period_type, period, band)
            off_rw = _d(off["cumulative_RW"])
            full_delta = _d(full["cumulative_RW"]) - off_rw
            checkable_delta = _d(checkable["cumulative_RW"]) - off_rw
            savings_delta = _d(savings_cd["cumulative_RW"]) - off_rw
            residual = full_delta - checkable_delta - savings_delta
            credit_delta_rw = _d(credit["cumulative_RW"]) - off_rw
            both_delta_rw = _d(both["cumulative_RW"]) - off_rw
            interaction = both_delta_rw - credit_delta_rw - full_delta
            common = {
                "experiment_id": EXPERIMENT_ID,
                "horizon_id": horizon_id,
                "period_type": period_type,
                "period": period,
                "dose_mode": dose_mode,
                "shock_size_bp": "100",
                "band": band,
                "label": LABEL,
                "off_RW": off["cumulative_RW"],
                "off_N_bil": off["cumulative_N_bil"],
                "off_D_bil": off["cumulative_D_bil"],
            }
            rows.append(
                common
                | {
                    "row_type": "bank_retention_sink",
                    "bank_payout_recycle_share": _fmt(PAYOUT_RECYCLE_SHARE_BANDS[band]),
                    "deposit_stock_delta_bil": _fmt(sink_deltas[(horizon_id, dose_mode)][band]),
                    "credit_deposit_stock_delta_bil": "",
                    "combined_deposit_stock_delta_bil": "",
                    "on_RW": full["cumulative_RW"],
                    "delta_RW": _fmt(full_delta),
                    "delta_RW_pct_of_off": _fmt(Decimal("0") if off_rw == 0 else full_delta / off_rw),
                    "on_N_bil": full["cumulative_N_bil"],
                    "delta_N_bil": _fmt(_d(full["cumulative_N_bil"]) - _d(off["cumulative_N_bil"])),
                    "on_D_bil": full["cumulative_D_bil"],
                    "delta_D_bil": _fmt(_d(full["cumulative_D_bil"]) - _d(off["cumulative_D_bil"])),
                    "checkable_families_only_delta_RW": _fmt(checkable_delta),
                    "savings_cd_families_only_delta_RW": _fmt(savings_delta),
                    "family_subset_residual_delta_RW": _fmt(residual),
                    "credit_deposit_only_delta_RW": "",
                    "combined_sinks_delta_RW": "",
                    "pairwise_interaction_delta_RW": "",
                    "ablation_additivity_assumed": "false",
                    "rollup_path": str(output_root / "measurements" / dose_mode / horizon_key / "full" / "out_phase6_waterfall_scaffold.csv"),
                }
            )
            rows.append(
                common
                | {
                    "row_type": "combined_credit_deposit_plus_bank_retention",
                    "bank_payout_recycle_share": _fmt(PAYOUT_RECYCLE_SHARE_BANDS[band]),
                    "deposit_stock_delta_bil": _fmt(sink_deltas[(horizon_id, dose_mode)][band]),
                    "credit_deposit_stock_delta_bil": _fmt(credit_deltas[band]),
                    "combined_deposit_stock_delta_bil": _fmt(
                        sink_deltas[(horizon_id, dose_mode)][band] + credit_deltas[band]
                    ),
                    "on_RW": both["cumulative_RW"],
                    "delta_RW": _fmt(both_delta_rw),
                    "delta_RW_pct_of_off": _fmt(Decimal("0") if off_rw == 0 else both_delta_rw / off_rw),
                    "on_N_bil": both["cumulative_N_bil"],
                    "delta_N_bil": _fmt(_d(both["cumulative_N_bil"]) - _d(off["cumulative_N_bil"])),
                    "on_D_bil": both["cumulative_D_bil"],
                    "delta_D_bil": _fmt(_d(both["cumulative_D_bil"]) - _d(off["cumulative_D_bil"])),
                    "checkable_families_only_delta_RW": "",
                    "savings_cd_families_only_delta_RW": "",
                    "family_subset_residual_delta_RW": "",
                    "credit_deposit_only_delta_RW": _fmt(credit_delta_rw),
                    "combined_sinks_delta_RW": _fmt(both_delta_rw),
                    "pairwise_interaction_delta_RW": _fmt(interaction),
                    "ablation_additivity_assumed": "false",
                    "rollup_path": str(output_root / "measurements" / dose_mode / horizon_key / "combined_sinks" / "out_phase6_waterfall_scaffold.csv"),
                }
            )
    return rows


def _nii_components(result: object, band: str, horizon_id: str) -> dict[str, Decimal]:
    rows = [
        row
        for row in result.rows("out_bank_receipt_pay_ledger")  # type: ignore[attr-defined]
        if row["ledger_boundary"] == "depository_bank_only"
    ]
    years = {"2026"} if horizon_id == "year1_2026" else {str(year) for year in range(2026, 2036)}
    selected = [row for row in rows if row["year"] in years]
    earning_receipts = sum(
        _d(row["amount_bil"])
        for row in selected
        if row["ledger_side"] == "receipt" and row["line_item"] in BANK_EARNING_ASSET_RECEIPTS
    )
    loan_receipts = sum(
        _d(row["amount_bil"])
        for row in selected
        if row["ledger_side"] == "receipt" and row["line_item"] in LOAN_RECEIPTS_ONLY
    )
    deposit_paid = sum(
        _d(row["amount_bil"])
        for row in selected
        if row["ledger_side"] == "payment" and row["line_item"] == "deposit_interest_paid"
    )
    return {
        "earning_asset_receipts_bil": earning_receipts,
        "loan_receipts_only_bil": loan_receipts,
        "deposit_interest_paid_bil": deposit_paid,
        "earning_asset_nii_delta_bil": earning_receipts - deposit_paid,
    }


def _apply_bank_deposit_delta(
    rows: list[dict[str, str]],
    band: str,
    delta: Decimal,
    families: tuple[str, ...],
) -> None:
    targets = [
        row
        for row in rows
        if row["instrument_family"] in families and _issuer(row) == "banks"
    ]
    total = sum(_d(row[band]) for row in targets)
    if total == 0 or delta == 0:
        return
    if delta < 0 and -delta > total:
        delta = -total
    for row in targets:
        value = _d(row[band])
        row[band] = _fmt(value + delta * value / total)


def _invariant_rows(
    pack_dir: Path,
    off_builds: dict[str, object],
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    expected = build_v1(pack_dir, include_impulse_beta_comparator=False).rows(
        "out_phase6_waterfall_scaffold"
    )
    actual = off_builds[DEFAULT_DOSE_MODE].rows("out_phase6_waterfall_scaffold")  # type: ignore[attr-defined]
    base = next(
        row
        for row in rows
        if row["row_type"] == "bank_retention_sink"
        and row["band"] == "base"
        and row["dose_mode"] == DEFAULT_DOSE_MODE
        and row["horizon_id"] == "year1_2026"
    )
    residual = _d(base["family_subset_residual_delta_RW"])
    return [
        {
            "check_id": "default_off_byte_exact",
            "status": "pass" if expected == actual else "fail",
            "expected": str(len(expected)),
            "actual": str(len(actual)),
            "note": "OFF exported pack equals standard build_v1 phase6 waterfall rows",
        },
        {
            "check_id": "direction_check_base_year1_persistent",
            "status": "pass" if _d(base["delta_RW"]) < 0 else "review",
            "expected": "delta_RW<0",
            "actual": base["delta_RW"],
            "note": "negative means retained bank NII reduces measured RW by shrinking deposits",
        },
        {
            "check_id": "residual_value_asserted_base_year1_persistent",
            "status": "pass" if residual != 0 else "fail",
            "expected": "nonzero three-run residual",
            "actual": _fmt(residual),
            "note": "residual is full minus checkable-only minus savings/CD-only from independent runs",
        },
    ]


def _lineage_rows(output_root: Path) -> list[dict[str, str]]:
    return [
        {
            "artifact": "out_bank_retention_sink.csv",
            "path": str(output_root / "out_bank_retention_sink.csv"),
            "lineage_note": "ON/OFF, family ablations, credit-only, and combined rows are fresh build_v1 outputs from exported packs",
        },
        {
            "artifact": "out_bank_retention_nii_construction.csv",
            "path": str(output_root / "out_bank_retention_nii_construction.csv"),
            "lineage_note": "NII uses existing out_bank_receipt_pay_ledger depository-bank earning-asset receipts minus deposit interest paid",
        },
        {
            "artifact": "QT deposit leg",
            "path": "src/ratewall/rwtam/v1.py:out_qt_deposit_leg",
            "lineage_note": "scenario-only QT deposit destruction uses latest negative SOMA/QT runoff from absorption_mode_mix summary times modes A plus A_RRP nonbank share",
        },
    ]


def _caveat_rows() -> list[dict[str, str]]:
    return [
        {
            "caveat_id": "assumption_grade_promoted",
            "caveat_text": "Mechanism is promoted into the default baseline as an owner-flagged assumption-grade combined-sink band.",
        },
        {
            "caveat_id": "nii_boundary",
            "caveat_text": "The used NII boundary is depository-bank earning-asset receipts minus deposit interest; loan-only minus deposit interest is reported as a diagnostic because the existing ledger boundary would otherwise imply a retained-NII fall under hikes.",
        },
        {
            "caveat_id": "payout_recycle_lineage",
            "caveat_text": "Recycle share is owner-flagged L/B/H 0.45/0.60/0.75 using FDIC QBP / large-bank payout-ratio and expense-share directional support, not a fitted bank-income distribution model.",
        },
        {
            "caveat_id": "m2_perimeter_note",
            "caveat_text": "Deposit stocks are the M1/M2-perimeter domestic nonbank-public deposits. Cross-border payments can move deposits out of perimeter without system-wide destruction; the marginal trade response to the standard dose is third-order for N and remains in the FX demand layer.",
        },
        {
            "caveat_id": "identifiability",
            "caveat_text": "Ablations identify deposit-family subsets, not outcome routes; deposit interest, migration-base, and competition-beta channels co-move inside each family run.",
        },
    ]


def _write_measurement_rollups(
    output_root: Path,
    off_builds: dict[str, object],
    builds: dict[tuple[str, str, str], object],
) -> None:
    for dose_mode, result in off_builds.items():
        out_dir = output_root / "measurements" / dose_mode / "off"
        out_dir.mkdir(parents=True, exist_ok=True)
        _write_rows(
            out_dir / "out_phase6_waterfall_scaffold.csv",
            result.rows("out_phase6_waterfall_scaffold"),  # type: ignore[attr-defined]
        )
    for (horizon_key, variant, dose_mode), result in builds.items():
        out_dir = output_root / "measurements" / dose_mode / horizon_key / variant
        out_dir.mkdir(parents=True, exist_ok=True)
        _write_rows(
            out_dir / "out_phase6_waterfall_scaffold.csv",
            result.rows("out_phase6_waterfall_scaffold"),  # type: ignore[attr-defined]
        )


def _headline(
    result: object,
    period_type: str,
    period: str,
    band: str,
) -> dict[str, str]:
    return next(
        row
        for row in result.rows("out_phase6_waterfall_scaffold")  # type: ignore[attr-defined]
        if row["period_type"] == period_type
        and row["period"] == period
        and row["band"] == band
        and row["ricardian_offset"] == "0"
        and row["headline_status"] == "final_rw_full"
    )


def _issuer(row: dict[str, str]) -> str:
    prefix = "issuer="
    for part in row["cell_or_sector"].split("|"):
        if part.startswith(prefix):
            return part.removeprefix(prefix)
    return ""


def _horizon_key(horizon_id: str, dose_mode: str) -> str:
    return f"{horizon_id}_{dose_mode}"


def _clear_output_subdirs(output_root: Path) -> None:
    for name in ("packs", "measurements"):
        path = output_root / name
        if path.exists():
            shutil.rmtree(path)


def _markdown_table(title: str, rows: list[dict[str, str]], max_rows: int = 18) -> list[str]:
    if not rows:
        return ["", f"## {title}", "", "_No rows._"]
    fields = list(rows[0])
    lines = [
        "",
        f"## {title}",
        "",
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows[:max_rows]:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    if len(rows) > max_rows:
        lines.append(
            f"| ... {len(rows) - max_rows} more rows | "
            + " | ".join("" for _ in fields[1:])
            + " |"
        )
    return lines
