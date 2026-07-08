from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtam.derived_metrics import (
    DerivedMetricsResult,
    build_derived_metrics,
    write_derived_metrics_outputs,
    write_derived_metrics_report,
)
from ratewall.rwtam.rwpi import RwpiResult, build_rwpi, write_rwpi_outputs


def main() -> None:
    result = build_derived_metrics(Path("var/rwtam/v1"))
    paths = write_derived_metrics_outputs(result, Path("var/rwtam/metrics"))
    rwpi = build_rwpi(Path("configs/rwtam/packs"))
    write_rwpi_outputs(rwpi, Path("var/rwtam/scenarios/rwpi"))
    report_path = write_derived_metrics_report(result, Path("do/rwtam_metrics_pce_report_20260707.md"))
    _append_pce_report_sections(report_path, result, rwpi)
    print(report_path)
    for table_name in [
        "out_derived_metrics_invariant_check",
        "out_attenuation_multiplier",
        "out_fiscal_cost_per_unit_compression",
    ]:
        _print_table(paths[table_name], max_rows=12)


def _print_table(path: Path, max_rows: int) -> None:
    print(path)
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames or []
    print(",".join(fields))
    for row in rows[:max_rows]:
        print(",".join(row[field] for field in fields))
    if len(rows) > max_rows:
        print(f"... {len(rows) - max_rows} more rows")


def _append_pce_report_sections(path: Path, metrics: DerivedMetricsResult, rwpi: RwpiResult) -> None:
    lines = path.read_text(encoding="utf-8").rstrip().splitlines()
    lines.extend(
        [
            "",
            "## PCE Crosswalk",
            "",
            "Factor-6 disposition: offline BEA Table 2.3.5 / BLS relative-importance source rows were not present in repo data, so `0.85` remains assumption-grade with the pack's `0.8-1.0` range and a to-fetch marker.",
            "",
            "### Factor table",
            "",
            "| factor | low | base | high | grade | label | caveat |",
            "| --- | ---: | ---: | ---: | --- | --- | --- |",
        ]
    )
    for row in rwpi.rows("out_rwpi_pce_factor_table"):
        lines.append(
            f"| {row['factor_id']} | {row['low']} | {row['base']} | {row['high']} | {row['grade']} | {row['source_label']} | {row['caveat']} |"
        )
    lines.extend(
        [
            "",
            "### Ratio crosswalk",
            "",
            "| horizon | band | CPI-basis RW | m_D | m_N | RW_pi_PCE | discrepancy vs pack check |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in rwpi.rows("out_rwpi_pce_ratio_crosswalk"):
        lines.append(
            f"| {row['horizon']} | {row['band']} | {row['source_RW_ratio_CPI_basis']} | {row['m_D']} | {row['m_N']} | {row['RW_pi_PCE_ratio_basis']} | {row['discrepancy_vs_pack_check']} |"
        )
    lines.extend(
        [
            "",
            "### Caveats",
            "",
            "| caveat | verdict |",
            "| --- | --- |",
        ]
    )
    for row in rwpi.rows("out_rwpi_pce_caveat_rows"):
        lines.append(f"| {row['caveat_id']} | {row['verdict_condensed']} |")
    lines.extend(
        [
            "",
            "### Output gates",
            "",
            "| check | status |",
            "| --- | --- |",
        ]
    )
    for row in metrics.rows("out_derived_metrics_invariant_check"):
        lines.append(f"| {row['check_id']} | {row['status']} |")
    for row in rwpi.rows("out_rwpi_invariant_check"):
        lines.append(f"| {row['check_id']} | {row['status']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
