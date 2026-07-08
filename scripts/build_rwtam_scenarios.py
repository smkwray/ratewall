from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtam.scenarios import (
    build_all_distress_scenarios,
    build_crossing_shock_sweep,
    write_all_distress_scenarios,
    write_crossing_shock_sweep,
)


def main() -> None:
    results = build_all_distress_scenarios(Path("configs/rwtam/packs"))
    paths = write_all_distress_scenarios(results, Path("var/rwtam/scenarios"))
    sweep_path = write_crossing_shock_sweep(
        build_crossing_shock_sweep(Path("configs/rwtam/packs")),
        Path("var/rwtam/scenarios"),
    )
    print(sweep_path)
    for scenario_id, table_paths in paths.items():
        print(scenario_id)
        for table_name in [
            "out_distress_invariant_check",
            "out_distress_deadweight_drag_by_year",
            "out_distress_falsification_check",
        ]:
            _print_table(table_paths[table_name], max_rows=8)


def _print_table(path: Path, max_rows: int) -> None:
    print(path)
    if not path.exists():
        print("empty")
        return
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
