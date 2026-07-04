from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtas.slr_conditions import (
    build_slr_conditions_experiment,
    cleanup_stale_hysteresis_redo_artifacts,
    write_slr_conditions_outputs,
    write_slr_conditions_report,
)


def main() -> None:
    removed = cleanup_stale_hysteresis_redo_artifacts()
    result = build_slr_conditions_experiment(Path("configs/rwtas/packs"))
    paths = write_slr_conditions_outputs(result, Path("var/rwtas/scenarios/slr_conditions"))
    report = write_slr_conditions_report(result, Path("do/rwtas_slr_conditions_report_20260703.md"))
    print(report)
    print(f"removed_stale_hysteresis_redo_artifacts={len(removed)}")
    for table_name in [
        "out_slr_conditions_ranking",
        "out_slr_stimulus_leg",
        "out_slr_spectrum",
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
