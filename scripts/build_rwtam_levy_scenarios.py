from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtam.levy_scenarios import (
    build_levy_scenarios,
    write_levy_scenario_outputs,
    write_levy_scenarios_report,
)


def main() -> None:
    result = build_levy_scenarios(Path("configs/rwtam/packs"))
    paths = write_levy_scenario_outputs(result, Path("var/rwtam/scenarios/levy_scenarios"))
    report_path = write_levy_scenarios_report(result, Path("do/rwtam_levy_scenarios_report_20260704.md"))
    print(report_path)
    for table_name in [
        "out_levy_reissuance_comparative",
        "out_cycle_2022_24_readout",
        "out_corridor_floor_comparison",
        "out_distributional_incidence_per_100bp",
        "out_levy_invariant_check",
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
