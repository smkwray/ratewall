from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtam.hysteresis import (
    build_hysteresis_experiment,
    write_hysteresis_outputs,
    write_hysteresis_report,
)


def main() -> None:
    result = build_hysteresis_experiment(Path("configs/rwtam/packs"))
    paths = write_hysteresis_outputs(result, Path("var/rwtam/scenarios/hysteresis_engine_loop"))
    report_path = write_hysteresis_report(result, Path("do/rwtam_migration_engine_loop_report_20260703.md"))
    print(report_path)
    for table_name in [
        "out_hysteresis_r1_gate",
        "out_hysteresis_conditions",
        "out_response_curve",
    ]:
        _print_table(paths[table_name], max_rows=10)


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
