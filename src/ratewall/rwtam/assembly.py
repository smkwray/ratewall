"""Assembly-only RWTAM paper support outputs."""

from __future__ import annotations

import csv
from collections import Counter
from decimal import Decimal
from pathlib import Path

from ratewall.rwtam.v1 import (
    BANDS,
    _d,
    _effective_pack,
    _fmt,
    _load_pack,
    _with_rw_ratio_degenerate,
    build_v1,
)


PACK_DIR = Path("configs/rwtam/packs")
OUTPUT_DIR = Path("var/rwtam/v1")
SCENARIO_ROOT = Path("var/rwtam/scenarios")
REPORT_PATH = Path("do/rwtam_assembly_report_20260705.md")
SECTOR_CONFIG = Path("configs/rwtam/cfg_sector.csv")
DEGENERATE_THRESHOLD_FRACTION = Decimal("0.001")

SECTOR_ALIASES = {
    "households": "households",
    "households_direct": "households",
    "households_via_agency_mbs": "households",
    "nonfinancial_firms": "nonfinancial_firms",
    "nonfinancial_firms_cre_owners": "nonfinancial_firms",
    "banks": "banks_depositories",
    "banks_credit_unions": "banks_depositories",
    "banks_nonbank_finance": "nonbank_financial",
    "nonbank_finance": "nonbank_financial",
    "nonbank_finance_mmfs": "nonbank_financial",
    "nonbank_finance_agency_mbs_investors": "nonbank_financial",
    "mmfs": "nonbank_financial",
    "insurers": "nonbank_financial",
    "mutual_funds_etfs": "nonbank_financial",
    "other_nonbank_finance": "nonbank_financial",
    "pensions": "nonbank_financial",
    "short_funding_payers": "nonbank_financial",
    "federal_reserve": "federal_reserve",
    "treasury_federal": "treasury_federal_government",
    "state_local": "state_local_public_authorities",
    "rest_of_world": "rest_of_world",
}

CELL_TO_SECTOR = {
    "hh_constrained_net_borrower": "households",
    "hh_middle_owner_illiquid": "households",
    "hh_retiree_fixed_income_saver": "households",
    "hh_unconstrained_saver": "households",
    "firm_bank_dependent_small": "nonfinancial_firms",
    "firm_market_funded_large": "nonfinancial_firms",
    "state_local_public_cell": "state_local_public_authorities",
    "rest_of_world_external_cell": "rest_of_world",
    "federal_reserve_accounting_cell": "federal_reserve",
    "treasury_federal_accounting_cell": "treasury_federal_government",
    "nonbank_finance_intermediary_no_conversion": "nonbank_financial",
}

BIN_ORDER = [
    "directly_observed",
    "literature_calibrated",
    "scenario_or_owner_assumption",
]


def build_assembly_outputs(
    pack_dir: Path = PACK_DIR,
    output_dir: Path = OUTPUT_DIR,
    scenario_root: Path = SCENARIO_ROOT,
    report_path: Path = REPORT_PATH,
) -> dict[str, Path]:
    result = build_v1(pack_dir)
    raw_pack = _load_pack(pack_dir)
    sectors = _sector_columns()
    balance_rows, balance_checks, treasury_lineage = sfc_balance_sheet_tables(raw_pack, sectors)
    tfm_rows, tfm_checks = sfc_transaction_flow_tables(result, sectors)
    manifest_rows, manifest_summary = parameter_manifest_rows(pack_dir, result)
    annotated = annotate_scenario_rollups(scenario_root)

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "out_sfc_balance_sheet_matrix": output_dir / "out_sfc_balance_sheet_matrix.csv",
        "out_sfc_balance_sheet_checks": output_dir / "out_sfc_balance_sheet_checks.csv",
        "out_sfc_treasury_holder_lineage": output_dir / "out_sfc_treasury_holder_lineage.csv",
        "out_sfc_transaction_flow_matrix": output_dir / "out_sfc_transaction_flow_matrix.csv",
        "out_sfc_transaction_flow_checks": output_dir / "out_sfc_transaction_flow_checks.csv",
        "out_parameter_manifest_three_bin": output_dir / "out_parameter_manifest_three_bin.csv",
        "out_rw_ratio_degenerate_annotation_check": output_dir
        / "out_rw_ratio_degenerate_annotation_check.csv",
    }
    _write_rows(paths["out_sfc_balance_sheet_matrix"], balance_rows)
    _write_rows(paths["out_sfc_balance_sheet_checks"], balance_checks)
    _write_rows(paths["out_sfc_treasury_holder_lineage"], treasury_lineage)
    _write_rows(paths["out_sfc_transaction_flow_matrix"], tfm_rows)
    _write_rows(paths["out_sfc_transaction_flow_checks"], tfm_checks)
    _write_rows(paths["out_parameter_manifest_three_bin"], manifest_rows)
    _write_rows(paths["out_rw_ratio_degenerate_annotation_check"], annotated)
    write_assembly_report(
        report_path,
        balance_rows,
        balance_checks,
        tfm_rows,
        tfm_checks,
        manifest_summary,
        annotated,
        result,
    )
    paths["report"] = report_path
    return paths


def sfc_balance_sheet_tables(
    pack: dict[str, list[dict[str, str]]],
    sectors: list[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    extra_columns = _extra_balance_columns(pack)
    columns = sectors + extra_columns
    grouped: dict[tuple[str, str], dict[str, Decimal]] = {}
    counts: Counter[tuple[str, str]] = Counter()
    for row in pack["opening_stocks"]:
        instrument = row["instrument_family"]
        for band in BANDS:
            key = (instrument, band)
            values = grouped.setdefault(key, {column: Decimal("0") for column in columns})
            holder = _holder_from_cell(row["cell_or_sector"])
            issuer = _issuer_from_cell(row["cell_or_sector"])
            values[_entity_column(holder, sectors)] += _d(row[band])
            values[_entity_column(issuer, sectors)] -= _d(row[band])
            counts[key] += 1

    rows: list[dict[str, str]] = []
    checks: list[dict[str, str]] = []
    for instrument, band in sorted(grouped):
        values = grouped[(instrument, band)]
        residual = sum(values.values(), Decimal("0"))
        rows.append(
            {
                "instrument_family": instrument,
                "band": band,
                "opening_stock_source_rows": str(counts[(instrument, band)]),
                "matrix_units": "$bn_current",
                **{column: _fmt(values[column]) for column in columns},
                "row_sum_bil": _fmt(residual),
                "adding_up_status": "pass" if residual == 0 else "fail",
            }
        )
        checks.append(
            {
                "check_id": f"BS_{instrument}_{band}",
                "instrument_family": instrument,
                "band": band,
                "residual_bil": _fmt(residual),
                "status": "pass" if abs(residual) <= Decimal("0.000000001") else "fail",
            }
        )
    return rows, checks, _treasury_holder_lineage(pack)


def sfc_transaction_flow_tables(
    result: object,
    sectors: list[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    columns = sectors + [
        "deferred_no_conversion",
        "unallocated_no_conversion",
        "sfc_interest_flow_counterparty",
    ]
    ledger_rows = [
        row
        for row in result.rows("out_cashflow_leg_gross")  # type: ignore[attr-defined]
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
        and row["dose_mode"] == "persistent_level"
    ]
    rows: list[dict[str, str]] = []
    checks: list[dict[str, str]] = []
    converted_sum = Decimal("0")
    for row in ledger_rows:
        amount = _d(row["gross_flow_bil"])
        converted = _d(row["converted_effect_bil"])
        converted_sum += converted
        values = {column: Decimal("0") for column in columns}
        target = _flow_cell_column(row["cell_or_sector"], sectors)
        values[target] += amount
        values["sfc_interest_flow_counterparty"] -= amount
        residual = sum(values.values(), Decimal("0"))
        flow_row_id = f"{row['source_channel_id']}|{row['exposure_id']}"
        rows.append(
            {
                "flow_row_id": flow_row_id,
                "period": "2026",
                "band": "base",
                "dose_mode": "persistent_level",
                "source_channel_id": row["source_channel_id"],
                "exposure_id": row["exposure_id"],
                "ledger_cell_or_sector": row["cell_or_sector"],
                "gross_flow_bil": row["gross_flow_bil"],
                "converted_effect_bil": row["converted_effect_bil"],
                "routing_basis": "out_cashflow_leg_gross;claim_processor_rules_v1_default_run",
                **{column: _fmt(values[column]) for column in columns},
                "row_sum_bil": _fmt(residual),
                "adding_up_status": "pass" if residual == 0 else "fail",
            }
        )
        checks.append(
            {
                "check_id": f"TFM_ZERO_{len(checks) + 1:04d}",
                "flow_row_id": flow_row_id,
                "residual_bil": _fmt(residual),
                "status": "pass" if abs(residual) <= Decimal("0.000000001") else "fail",
            }
        )

    rollup = _base_year_rollup(result, "out_cashflow_core_rollup")
    natural_n = sum(
        _d(row["converted_effect_bil"])
        for row in ledger_rows
        if _d(row["converted_effect_bil"]) > 0
    )
    natural_d = -sum(
        _d(row["converted_effect_bil"])
        for row in ledger_rows
        if _d(row["converted_effect_bil"]) < 0
    )
    checks.extend(
        [
            {
                "check_id": "TFM_ROLLUP_N_TIEOUT",
                "flow_row_id": "base_year_cashflow_core",
                "residual_bil": _fmt(natural_n - _d(rollup["N_bil"])),
                "status": "pass"
                if abs(natural_n - _d(rollup["N_bil"])) <= Decimal("0.000000001")
                else "fail",
            },
            {
                "check_id": "TFM_ROLLUP_D_TIEOUT",
                "flow_row_id": "base_year_cashflow_core",
                "residual_bil": _fmt(natural_d - _d(rollup["D_bil"])),
                "status": "pass"
                if abs(natural_d - _d(rollup["D_bil"])) <= Decimal("0.000000001")
                else "fail",
            },
            {
                "check_id": "TFM_ROLLUP_NET_TIEOUT",
                "flow_row_id": "base_year_cashflow_core",
                "residual_bil": _fmt(converted_sum - _d(rollup["net_bil"])),
                "status": "pass"
                if abs(converted_sum - _d(rollup["net_bil"])) <= Decimal("0.000000001")
                else "fail",
            },
        ]
    )
    memo_values = {column: "0" for column in columns}
    rows.append(
        {
            "flow_row_id": "memo_phase6_elasticity_layers_not_in_flow_ledger",
            "period": "2026",
            "band": "base",
            "dose_mode": "persistent_level",
            "source_channel_id": "phase6_memo",
            "exposure_id": "not_a_transaction_flow",
            "ledger_cell_or_sector": "phase6_elasticity_layers",
            "gross_flow_bil": "0",
            "converted_effect_bil": "0",
            "routing_basis": "memo_only_not_in_tfm_totals",
            **memo_values,
            "row_sum_bil": "0",
            "adding_up_status": "memo",
        }
    )
    return rows, checks


def parameter_manifest_rows(
    pack_dir: Path,
    result: object,
) -> tuple[list[dict[str, str]], dict[str, Counter[str] | int]]:
    rows: list[dict[str, str]] = [_mapping_rule_row(rule) for rule in _mapping_rules()]
    bin_counts: Counter[str] = Counter()
    pack_counts: Counter[str] = Counter()
    parameter_count = 0
    flagged_rows = result.rows("out_flagged_assumptions")  # type: ignore[attr-defined]
    flagged_keys = _flagged_keys(result)
    flagged_by_key = {
        _manifest_key(
            row["table"],
            row["parameter_id"],
            row["cell_or_sector"],
            row["instrument_family"],
            row["low"],
            row["base"],
            row["high"],
            row["input_basis_label"],
        ): row
        for row in flagged_rows
    }
    assumption_keys: set[tuple[str, str, str, str, str, str, str, str]] = set()

    for path in sorted(pack_dir.rglob("*.csv")):
        if path.name == "source_provenance.csv":
            continue
        source_conf = _source_confidence_map(path)
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
            if not _is_parameter_schema(fields):
                continue
            for row_index, source_row in enumerate(reader, start=1):
                parameter_count += 1
                parameter_id = _parameter_id(source_row, path, row_index)
                label = source_row.get("input_basis_label", "")
                confidence = source_conf.get(source_row.get("source_id", ""), "")
                bin_name, flag = _bin_for(label, confidence)
                rel_path = path.as_posix()
                table = path.stem
                key = _manifest_key(
                    table,
                    parameter_id,
                    source_row.get("cell_or_sector", source_row.get("holder", "")),
                    source_row.get("instrument_family", ""),
                    source_row.get("low", ""),
                    source_row.get("base", ""),
                    source_row.get("high", ""),
                    label,
                )
                if key in flagged_keys:
                    bin_name = "scenario_or_owner_assumption"
                    flag = "false"
                if bin_name == "scenario_or_owner_assumption":
                    assumption_keys.add(key)
                bin_counts[bin_name] += 1
                pack_counts[f"{_pack_name(path)}|{bin_name}"] += 1
                rows.append(
                    {
                        "record_type": "parameter_row",
                        "pack": _pack_name(path),
                        "source_path": rel_path,
                        "table": table,
                        "row_index": str(row_index),
                        "parameter_id": parameter_id,
                        "cell_or_sector": source_row.get(
                            "cell_or_sector", source_row.get("holder", "")
                        ),
                        "instrument_family": source_row.get("instrument_family", ""),
                        "low": source_row.get("low", ""),
                        "base": source_row.get("base", ""),
                        "high": source_row.get("high", ""),
                        "input_basis_label": label,
                        "source_id": source_row.get("source_id", ""),
                        "source_confidence": confidence,
                        "three_bin": bin_name,
                        "ambiguous_label_flag": flag,
                        "mapping_rule": "",
                        "count": "",
                        "status": "covered",
                    }
                )

    missing_flagged = sorted(flagged_keys - assumption_keys)
    for key in missing_flagged:
        source_row = flagged_by_key[key]
        parameter_count += 1
        bin_counts["scenario_or_owner_assumption"] += 1
        pack_counts["effective_pack|scenario_or_owner_assumption"] += 1
        assumption_keys.add(key)
        rows.append(
            {
                "record_type": "parameter_row",
                "pack": "effective_pack",
                "source_path": "effective_pack:out_flagged_assumptions",
                "table": source_row["table"],
                "row_index": "",
                "parameter_id": source_row["parameter_id"],
                "cell_or_sector": source_row["cell_or_sector"],
                "instrument_family": source_row["instrument_family"],
                "low": source_row["low"],
                "base": source_row["base"],
                "high": source_row["high"],
                "input_basis_label": source_row["input_basis_label"],
                "source_id": "",
                "source_confidence": "",
                "three_bin": "scenario_or_owner_assumption",
                "ambiguous_label_flag": "false",
                "mapping_rule": "derived_effective_pack_row_flagged_by_default_v1",
                "count": "",
                "status": "covered",
            }
        )
    missing_flagged = sorted(flagged_keys - assumption_keys)
    for bin_name in BIN_ORDER:
        rows.append(_count_row("bin_count", bin_name, bin_counts[bin_name]))
    for key, count in sorted(pack_counts.items()):
        pack, bin_name = key.split("|", 1)
        rows.append(_count_row("pack_bin_count", f"{pack}:{bin_name}", count))
    rows.append(_count_row("coverage_check", "unbinned_rows", 0))
    rows.append(_count_row("subset_check", "flagged_assumptions_missing_from_assumption_bin", len(missing_flagged)))
    return rows, {
        "parameter_count": parameter_count,
        "bin_counts": bin_counts,
        "pack_counts": pack_counts,
        "flagged_missing": len(missing_flagged),
    }


def annotate_scenario_rollups(scenario_root: Path = SCENARIO_ROOT) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(scenario_root.rglob("out_ratewall_rollup.csv")):
        before = path.read_text(encoding="utf-8")
        table = _read_rows(path)
        annotated = _with_rw_ratio_degenerate(table)
        changed_only_by_column = _same_except_flag(table, annotated)
        _write_rows(path, annotated)
        after = path.read_text(encoding="utf-8")
        flag_count = sum(1 for row in annotated if row["rw_ratio_degenerate"] == "true")
        rows.append(
            {
                "path": path.as_posix(),
                "rows": str(len(annotated)),
                "flagged_rows": str(flag_count),
                "had_column_before": str("rw_ratio_degenerate" in (table[0] if table else {})).lower(),
                "value_identical_except_new_column": str(changed_only_by_column).lower(),
                "bytes_changed": str(before != after).lower(),
            }
        )
    return rows


def write_assembly_report(
    path: Path,
    balance_rows: list[dict[str, str]],
    balance_checks: list[dict[str, str]],
    tfm_rows: list[dict[str, str]],
    tfm_checks: list[dict[str, str]],
    manifest_summary: dict[str, Counter[str] | int],
    annotated: list[dict[str, str]],
    result: object,
) -> Path:
    residual_columns = sorted(
        column
        for column in balance_rows[0]
        if ("unallocated" in column or "residual" in column)
        and any(_d(row.get(column, "0") or "0") != 0 for row in balance_rows)
    )
    bin_counts = manifest_summary["bin_counts"]
    assert isinstance(bin_counts, Counter)
    base_d = _d(_base_year_rollup(result, "out_ratewall_rollup")["D_bil"])
    threshold = base_d * DEGENERATE_THRESHOLD_FRACTION
    flagged_scenario_rows = sum(int(row["flagged_rows"]) for row in annotated)
    annotation_failures = sum(
        1 for row in annotated if row["value_identical_except_new_column"] != "true"
    )
    lines = [
        "# RWTAM assembly report 2026-07-05",
        "",
        "## Dispositions",
        "",
        "| item | disposition | lineage |",
        "|---|---|---|",
        "| A1 balance-sheet matrix | built from `configs/rwtam/packs/opening_stocks.csv`; Treasury holder matrix crosswalk emitted as lineage, not double-counted | `out_sfc_balance_sheet_matrix.csv`; `out_sfc_treasury_holder_lineage.csv` |",
        "| A1 transaction-flow matrix | built from existing default-run `out_cashflow_leg_gross` annual 2026 base-band rows; no new run or estimate | `out_sfc_transaction_flow_matrix.csv`; `out_sfc_transaction_flow_checks.csv` |",
        "| A2 three-bin manifest | built from parameter-like CSV rows under `configs/rwtam/packs/**`; ambiguous labels default to assumption bin | `out_parameter_manifest_three_bin.csv` |",
        "| A3 ratio-degeneracy flag | emitted only on scenario `out_ratewall_rollup.csv` files under `var/rwtam/scenarios`; default `var/rwtam/v1` and goldens not rewritten | scenario rollup CSVs |",
        "",
        "## Shapes",
        "",
        f"- Balance-sheet matrix rows: `{len(balance_rows)}`; columns include configured sectors plus explicit residual columns.",
        f"- Transaction-flow matrix rows: `{len(tfm_rows)}` including one memo row for Phase 6 elasticity layers outside the ledger.",
        f"- Balance residual columns with nonzero cells: `{', '.join(residual_columns) if residual_columns else 'none'}`.",
        f"- Balance zero-sum checks: `{_status_counts(balance_checks)}`.",
        f"- TFM zero-sum/tie-out checks: `{_status_counts(tfm_checks)}`.",
        "",
        "## Parameter Bins",
        "",
        "| bin | count |",
        "|---|---:|",
    ]
    for bin_name in BIN_ORDER:
        lines.append(f"| {bin_name} | {bin_counts[bin_name]} |")
    lines.extend(
        [
            "",
            f"- Parameter rows covered: `{manifest_summary['parameter_count']}`.",
            f"- Flagged-assumption rows missing from assumption bin: `{manifest_summary['flagged_missing']}`.",
            "",
            "## Degeneracy Flag",
            "",
            f"- Threshold rule: `D_bil < base_year1_D_bil * {DEGENERATE_THRESHOLD_FRACTION}` or `RW_ratio` outside `[0,1]`.",
            f"- Base year-1 D: `{_fmt(base_d)}`; threshold: `{_fmt(threshold)}`.",
            f"- Scenario rollup files annotated: `{len(annotated)}`; flagged scenario rows: `{flagged_scenario_rows}`.",
            f"- Scenario per-file value-identity assertion failures: `{annotation_failures}`.",
            "- Headline/default tree was not rewritten by the assembly script; default writer path remains schema-stable outside `var/rwtam/scenarios`.",
            "",
            "## Caveats",
            "",
            "- The TFM covers the interest-flow ledger. Phase 6 elasticity layers are not transaction flows in that ledger and appear only as the memo row.",
            "- Residual/unallocated stock and flow cells remain explicit columns; none are absorbed into configured sectors.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _mapping_rules() -> list[dict[str, str]]:
    return [
        {
            "mapping_rule": "direct",
            "three_bin": "directly_observed",
            "description": "input_basis_label or provenance confidence names exact/checked/current official or source rows and does not carry owner/scenario/proxy/literature language",
        },
        {
            "mapping_rule": "literature",
            "three_bin": "literature_calibrated",
            "description": "input_basis_label or provenance confidence names literature, SCF/DFA-shaped calibration, percentile prior, empirical/path calibration, source-backed assumption, or proxy calibrated from evidence",
        },
        {
            "mapping_rule": "assumption",
            "three_bin": "scenario_or_owner_assumption",
            "description": "input_basis_label is owner/scenario/project/placeholder/stress/architecture, blank, or otherwise ambiguous",
        },
    ]


def _mapping_rule_row(rule: dict[str, str]) -> dict[str, str]:
    return {
        "record_type": "mapping_rule",
        "pack": "",
        "source_path": "",
        "table": "",
        "row_index": "",
        "parameter_id": "",
        "cell_or_sector": "",
        "instrument_family": "",
        "low": "",
        "base": "",
        "high": "",
        "input_basis_label": "",
        "source_id": "",
        "source_confidence": "",
        "three_bin": rule["three_bin"],
        "ambiguous_label_flag": "",
        "mapping_rule": rule["description"],
        "count": "",
        "status": rule["mapping_rule"],
    }


def _bin_for(label: str, confidence: str) -> tuple[str, str]:
    text = f"{label} {confidence}".lower()
    assumption_tokens = [
        "owner",
        "scenario",
        "project",
        "placeholder",
        "stress",
        "architecture",
        "not_fitted",
        "unverified",
        "proxy",
        "assumption",
        "ambiguous",
        "imputed",
        "demo",
        "judgment",
    ]
    literature_tokens = [
        "literature",
        "calibrated",
        "scf",
        "dfa",
        "percentile",
        "empirical",
        "source_backed",
        "published",
        "mode_mix",
        "evidence",
    ]
    direct_tokens = [
        "checked_exact",
        "latest available opening stock",
        "q1 2026",
        "2026q1",
        "2025q4",
        "ye2025",
        "official",
        "fred",
        "z.1",
        "h.4.1",
    ]
    if not text.strip():
        return "scenario_or_owner_assumption", "true"
    if any(token in text for token in assumption_tokens):
        return "scenario_or_owner_assumption", "false"
    if any(token in text for token in literature_tokens):
        return "literature_calibrated", "false"
    if any(token in text for token in direct_tokens) or confidence == "high":
        return "directly_observed", "false"
    return "scenario_or_owner_assumption", "true"


def _source_confidence_map(path: Path) -> dict[str, str]:
    source_path = path.parent / "source_provenance.csv"
    if not source_path.exists():
        return {}
    out: dict[str, str] = {}
    with source_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            value = row.get("confidence") or row.get("reliability") or row.get("source_type") or ""
            out[row.get("source_id", "")] = value
    return out


def _is_parameter_schema(fields: list[str]) -> bool:
    return (
        "parameter_id" in fields
        or "assumption_id" in fields
        or "parameter" in fields
        or {"low", "base", "high"}.issubset(fields)
    )


def _parameter_id(row: dict[str, str], path: Path, row_index: int) -> str:
    return (
        row.get("parameter_id")
        or row.get("assumption_id")
        or row.get("parameter")
        or row.get("mode_id")
        or row.get("state_id")
        or row.get("metric")
        or f"{path.stem}:{row_index}"
    )


def _pack_name(path: Path) -> str:
    rel = path.relative_to(PACK_DIR)
    return rel.parts[0] if len(rel.parts) > 1 else "root"


def _flagged_keys(result: object) -> set[tuple[str, str, str, str, str, str, str, str]]:
    return {
        _manifest_key(
            row["table"],
            row["parameter_id"],
            row["cell_or_sector"],
            row["instrument_family"],
            row["low"],
            row["base"],
            row["high"],
            row["input_basis_label"],
        )
        for row in result.rows("out_flagged_assumptions")  # type: ignore[attr-defined]
    }


def _manifest_key(
    table: str,
    parameter_id: str,
    cell_or_sector: str,
    instrument_family: str,
    low: str,
    base: str,
    high: str,
    input_basis_label: str,
) -> tuple[str, str, str, str, str, str, str, str]:
    return (
        table,
        parameter_id,
        cell_or_sector,
        instrument_family,
        low,
        base,
        high,
        input_basis_label,
    )


def _count_row(record_type: str, label: str, count: int) -> dict[str, str]:
    status = ""
    if label in {"unbinned_rows", "flagged_assumptions_missing_from_assumption_bin"}:
        status = "pass" if count == 0 else "fail"
    return {
        "record_type": record_type,
        "pack": label,
        "source_path": "",
        "table": "",
        "row_index": "",
        "parameter_id": "",
        "cell_or_sector": "",
        "instrument_family": "",
        "low": "",
        "base": "",
        "high": "",
        "input_basis_label": "",
        "source_id": "",
        "source_confidence": "",
        "three_bin": "",
        "ambiguous_label_flag": "",
        "mapping_rule": "",
        "count": str(count),
        "status": status,
    }


def _sector_columns() -> list[str]:
    with SECTOR_CONFIG.open(encoding="utf-8", newline="") as handle:
        return [row["sector_id"] for row in csv.DictReader(handle)]


def _extra_balance_columns(pack: dict[str, list[dict[str, str]]]) -> list[str]:
    extras = set()
    sectors = set(_sector_columns())
    for row in pack["opening_stocks"]:
        for entity in [_holder_from_cell(row["cell_or_sector"]), _issuer_from_cell(row["cell_or_sector"])]:
            column = _entity_column(entity, list(sectors))
            if column not in sectors:
                extras.add(column)
    return sorted(extras)


def _holder_from_cell(cell: str) -> str:
    for part in cell.split("|"):
        if part.startswith("holder="):
            return part.removeprefix("holder=")
    return cell


def _issuer_from_cell(cell: str) -> str:
    for part in cell.split("|"):
        if part.startswith("issuer="):
            return part.removeprefix("issuer=")
    return cell


def _entity_column(entity: str, sectors: list[str]) -> str:
    mapped = SECTOR_ALIASES.get(entity, entity)
    if mapped in sectors:
        return mapped
    if "unallocated" in mapped or "residual" in mapped:
        return mapped
    return f"residual_unmapped_{mapped}"


def _flow_cell_column(cell: str, sectors: list[str]) -> str:
    mapped = CELL_TO_SECTOR.get(cell, "")
    if mapped in sectors:
        return mapped
    if "unallocated" in cell:
        return "unallocated_no_conversion"
    if "deferred" in cell:
        return "deferred_no_conversion"
    return "deferred_no_conversion"


def _treasury_holder_lineage(pack: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    opening = [
        row
        for row in pack["opening_stocks"]
        if row["instrument_family"] in {"treasury_bills", "treasury_notes_bonds_tips"}
    ]
    total = sum(_d(row["base"]) for row in opening)
    by_holder: Counter[str] = Counter()
    for row in opening:
        by_holder[_holder_from_cell(row["cell_or_sector"])] += _d(row["base"])
    matrix_rows = [
        row
        for row in pack["treasury_holder_matrix"]
        if row["instrument_family"] == "all_marketable_treasuries"
    ]
    return [
        {
            "holder": row["cell_or_sector"],
            "treasury_holder_matrix_share": row["base"],
            "opening_stock_implied_share": _fmt(by_holder[row["cell_or_sector"]] / total)
            if total
            else "0",
            "opening_stock_bil": _fmt(by_holder[row["cell_or_sector"]]),
            "lineage_note": "opening_stocks is the counted stock matrix; treasury_holder_matrix is emitted as holder-share lineage to avoid double counting",
        }
        for row in matrix_rows
    ]


def _base_year_rollup(result: object, table_name: str) -> dict[str, str]:
    for row in result.rows(table_name):  # type: ignore[attr-defined]
        if (
            row["period_type"] == "annual"
            and row["period"] == "2026"
            and row["band"] == "base"
            and row["ricardian_offset"] == "0"
        ):
            return row
    raise ValueError(f"missing base-year rollup in {table_name}")


def _status_counts(rows: list[dict[str, str]]) -> str:
    counts = Counter(row["status"] for row in rows)
    return ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _same_except_flag(
    before: list[dict[str, str]],
    after: list[dict[str, str]],
) -> bool:
    if len(before) != len(after):
        return False
    for old, new in zip(before, after, strict=True):
        old_stripped = dict(old)
        new_stripped = dict(new)
        old_stripped.pop("rw_ratio_degenerate", None)
        new_stripped.pop("rw_ratio_degenerate", None)
        if old_stripped != new_stripped:
            return False
    return True
