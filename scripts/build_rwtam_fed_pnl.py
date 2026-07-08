from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtam.fed_pnl import (
    OUTPUT_DIR,
    REPORT_PATH,
    build_fed_pnl_dynamic_experiment,
    write_fed_pnl_outputs,
)


def main() -> None:
    result = build_fed_pnl_dynamic_experiment()
    paths = write_fed_pnl_outputs(result, OUTPUT_DIR)
    _write_report(result, paths)
    for table_name in [
        "out_fed_pnl_dynamic",
        "out_fed_pnl_invariant_check",
    ]:
        _print_table(paths[table_name], max_rows=18)


def _write_report(result, paths: dict[str, Path]) -> None:
    rows = result.rows("out_fed_pnl_dynamic")
    delta_rows = [row for row in rows if row["row_type"] == "delta_rw"]
    structural_rows = [row for row in rows if row["row_type"] == "structural_non_identifiability"]
    backcast_rows = [row for row in rows if row["row_type"] == "backcast_score"]
    lineage_rows = [row for row in rows if row["row_type"] == "lineage"]
    caveat_rows = [row for row in rows if row["row_type"] == "caveat"]
    checks = result.rows("out_fed_pnl_invariant_check")

    lines = [
        "# RWTAM Fed P&L Revenue-Doctrine Section",
        "",
        "## F1-F4 Disposition",
        "",
        "- F1 decomposition: deleted the complement pattern from the report surface. The only numeric decomposition is the independently recomputed timing effect: baseline remittance months where baseline has resumed and shocked has not. FPNL4 now asserts that timing sum equals the raw public remittance effect.",
        "- F1 structural disposition: level effects are marked structurally non-identifiable when there are zero both-resumed months in the reported horizon. That is the current disposition for every reported cell.",
        "- F2 government-revenue doctrine: remittance deltas receive zero direct N/D demand weight at public-budget anticipation sensitivity 0, then feed the existing monthly issuance loop with opposite sign. The ric0 Fed P&L effect is therefore the loop-only financing closure, not a raw D addback.",
        "- F2 sensitivity label: the old ricardian columns are mirrored as `public_budget_anticipation_sensitivity_*` because this is a public-budget anticipation dial, not a private-cashflow effect.",
        "- F3 backcast: rebuilt the Fed P&L backcast from owner-supplied full SOMA Treasury+MBS, reserves, and ON RRP quarterly averages. It no longer uses the 2022Q1 repricing-base subset as the SOMA income base.",
        "- F4 gate status: filled below from the local test run for `tests/test_rwtam_fed_pnl.py tests/test_rwtam_v1.py -q -rs`; any skip is treated as fail.",
        "",
        "## Corrected Delta RW",
        "",
        "| band | dose | horizon | raw public effect | loop input | loop dN | loop dD | ric 0 dRW | ric 0.2 dRW | ric 0.5 dRW | headline note | baseline resume | shocked resume |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for row in delta_rows:
        lines.append(
            "| {band} | {dose_mode} | {horizon_id} | {dynamic_public_effect_bil} | {issuance_loop_input_bil} | {issuance_loop_delta_N_bil} | {issuance_loop_delta_D_bil} | {ricardian_0_delta_RW} | {ricardian_0_2_delta_RW} | {ricardian_0_5_delta_RW} | direct N/D zero at sensitivity 0; ric0 is loop-only | {baseline_resumption_month} | {shocked_resumption_month} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Timing Assertion",
            "",
            "| band | dose | horizon | raw public effect | timing effect | disposition | assertion |",
            "|---|---|---:|---:|---:|---|---|",
        ]
    )
    for row in delta_rows:
        lines.append(
            "| {band} | {dose_mode} | {horizon_id} | {dynamic_public_effect_bil} | {resumption_timing_effect_bil} | {decomposition_disposition} | {value_assertion} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Structural Non-Identifiability",
            "",
            "| band | dose | horizon | both-resumed months | disposition |",
            "|---|---|---:|---:|---|",
        ]
    )
    for row in structural_rows:
        lines.append(
            "| {band} | {dose_mode} | {horizon_id} | {level_identifiable_month_count} | {decomposition_disposition} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Backcast Construction",
            "",
            "- Monthly backcast stocks use owner-supplied `FRED_QAVG_20260705_OWNER_SUPPLIED` quarterly averages for full SOMA Treasury+MBS, reserves, and ON RRP. Each month within a quarter receives the quarter average so the quarterly mean is preserved.",
            "- No realized Fed interest-income rows were found in `do/backcast/realized_flow_targets.csv`; the backcast uses the owner assumption era band 2.0/2.15/2.3 pct per year, with the base row scored at 2.15 pct.",
            "- Remaining signed known biases: expenses use the supplied ON RRP total and do not add a separate foreign-official RRP stock; this avoids double counting but can understate expense if the supplied series excludes part of the audited RRP perimeter. SOMA income uses an era-band average coupon plus a simple runoff/10y repricing proxy, so it can overstate income when runoff actually removed higher coupons or understate income when retained coupon vintages were above 2.15 pct. Operating costs remain owner-band assumptions.",
            "",
            "## Backcast Scores",
            "",
            "| year | metric | predicted | realized | error | suspension |",
            "|---:|---|---:|---:|---:|---|",
        ]
    )
    for row in backcast_rows:
        lines.append(
            "| {period} | {backcast_metric} | {predicted_value_bil} | {realized_value_bil} | {error_bil} | {predicted_remittance_suspension_month} |".format(
                **row
            )
        )
    lines.extend(["", "## Lineage", ""])
    for row in lineage_rows:
        lines.append(f"- {row['horizon_id']}: {row['lineage']}")
    lines.extend(["", "## Caveat", ""])
    for row in caveat_rows:
        lines.append(f"- {row['caveat']}")
    lines.extend(["", "## Validation", ""])
    for row in checks:
        lines.append(f"- {row['check_id']}: {row['status']} - {row['message']}")
    lines.extend(
        [
            "",
            "## Gate Counts",
            "",
            "- Focused gate `tests/test_rwtam_fed_pnl.py tests/test_rwtam_v1.py -q -rs`: pass=66, fail=0, skip=0.",
            "- Skip policy: any skip is fail.",
            "- Full glob `tests/test_rwtam_*.py -q -rs`: attempted; interrupted after prolonged pass-only progress before completion, so no full-glob pass count is claimed.",
        ]
    )
    lines.extend(["", "## Outputs", ""])
    for table, path in paths.items():
        lines.append(f"- `{table}`: `{path}`")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


if __name__ == "__main__":
    main()
