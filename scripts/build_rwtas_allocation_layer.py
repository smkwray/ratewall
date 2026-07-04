from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtas.allocation_layer import (
    build_allocation_layer,
    write_allocation_layer_outputs,
    write_allocation_layer_report,
)


def main() -> None:
    result = build_allocation_layer(Path("configs/rwtas/packs"))
    paths = write_allocation_layer_outputs(result, Path("var/rwtas/scenarios/allocation_layer"))
    report = write_allocation_layer_report(result, Path("do/rwtas_allocation_fix_report_20260703.md"))
    print(paths["out_allocation_layer_diagnostic"])
    _print_table(paths["out_allocation_on_off"], max_rows=8)
    _print_table(paths["out_allocation_overlap_probe"], max_rows=8)
    print(report)


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
