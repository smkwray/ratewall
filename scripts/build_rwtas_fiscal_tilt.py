from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtas.fiscal_tilt import (
    build_fiscal_tilt_experiment,
    write_fiscal_tilt_outputs,
    write_fiscal_tilt_report,
)


def main() -> None:
    result = build_fiscal_tilt_experiment(Path("configs/rwtas/packs"))
    paths = write_fiscal_tilt_outputs(result, Path("var/rwtas/scenarios/fiscal_tilt"))
    report = write_fiscal_tilt_report(result, Path("do/rwtas_fiscal_tilt_report_20260704.md"))
    print(report)
    for table_name in [
        "out_fiscal_tilt_invariant_check",
        "out_fiscal_tilt_grid",
        "out_fiscal_tilt_ablation",
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


if __name__ == "__main__":
    main()
