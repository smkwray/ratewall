from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtas.reissuance_policy import (
    build_reissuance_policy_scenarios,
    write_reissuance_m0_fix_report,
    write_reissuance_policy_outputs,
    write_reissuance_policy_report,
)


def main() -> None:
    results = build_reissuance_policy_scenarios(Path("configs/rwtas/packs"))
    paths = write_reissuance_policy_outputs(results, Path("var/rwtas/scenarios/reissuance_policy"))
    report_path = write_reissuance_policy_report(
        results,
        Path("do/rwtas_reissuance_policy_report_20260702.md"),
    )
    m0_report_path = write_reissuance_m0_fix_report(
        results,
        Path("do/rwtas_m0_reissuance_fix_report_20260702.md"),
    )
    print(report_path)
    print(m0_report_path)
    print(paths["out_reissuance_divergence_vs_base"])
    _print_table(Path(paths["out_reissuance_divergence_vs_base"]), max_rows=12)


def _print_table(path: Path, max_rows: int) -> None:
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
